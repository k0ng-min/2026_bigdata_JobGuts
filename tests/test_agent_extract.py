import json
import tempfile
import unittest
from pathlib import Path

from src.agent.extract import (
    candidate_names,
    extract_candidates,
    load_korean_spellings,
    load_stopwords,
    split_compound,
)


def _stopwords(words=("and", "based", "the", "with")):
    temp_dir = tempfile.TemporaryDirectory()
    path = Path(temp_dir.name) / "stopwords.json"
    path.write_text(json.dumps({"version": "test.v1", "stopwords": list(words)}), encoding="utf-8")
    return temp_dir, load_stopwords(path)


class SymbolPreservationTests(unittest.TestCase):
    """C, C++ and C# are three different technologies and must stay apart."""

    def setUp(self):
        temp_dir, self.stopwords = _stopwords()
        self.addCleanup(temp_dir.cleanup)

    def test_plus_and_hash_suffixes_survive_extraction(self):
        names = set(candidate_names("C, C++, C# 개발 경험", self.stopwords))

        self.assertEqual(names, {"C", "C++", "C#"})

    def test_c_family_names_do_not_collapse_into_one_candidate(self):
        names = candidate_names("C++ 와 C# 를 모두 씁니다", self.stopwords)

        self.assertIn("C++", names)
        self.assertIn("C#", names)
        self.assertNotIn("C", names)

    def test_leading_and_internal_dots_survive_extraction(self):
        names = set(candidate_names("Node.js, Vue.js, ASP.NET, .NET 사용", self.stopwords))

        self.assertEqual(names, {"Node.js", "Vue.js", "ASP.NET", ".NET"})

    def test_a_trailing_sentence_dot_is_not_part_of_the_name(self):
        self.assertEqual(candidate_names("Python.", self.stopwords), ("Python",))

    def test_a_single_letter_counts_only_when_written_in_upper_case(self):
        self.assertIn("R", candidate_names("R 과 통계 분석", self.stopwords))
        self.assertNotIn("a", candidate_names("a 프로젝트", self.stopwords))


class HyphenCompoundTests(unittest.TestCase):
    """Wi-Fi is one name; splitting it invented a Wi -> Fi rule at interest 0.98."""

    def setUp(self):
        temp_dir, self.stopwords = _stopwords()
        self.addCleanup(temp_dir.cleanup)

    def test_wifi_stays_whole_and_never_yields_its_fragments(self):
        names = set(candidate_names("Wi-Fi 환경 구축", self.stopwords))

        self.assertEqual(names, {"Wi-Fi"})
        self.assertNotIn("Wi", names)
        self.assertNotIn("Fi", names)

    def test_objective_c_stays_whole_so_it_cannot_inflate_the_count_of_c(self):
        names = set(candidate_names("Objective-C 유지보수", self.stopwords))

        self.assertEqual(names, {"Objective-C"})
        self.assertNotIn("C", names)

    def test_a_hyphenated_qualifier_yields_the_technology_not_the_compound(self):
        names = set(candidate_names("Python-based 서비스", self.stopwords))

        self.assertEqual(names, {"Python"})

    def test_slash_compound_of_short_parts_stays_whole(self):
        self.assertEqual(set(candidate_names("CI/CD 파이프라인", self.stopwords)), {"CI/CD"})
        self.assertEqual(set(candidate_names("TCP/IP 통신", self.stopwords)), {"TCP/IP"})

    def test_slash_compound_of_long_parts_yields_the_parts(self):
        names = set(candidate_names("HTML/CSS/JavaScript 작업", self.stopwords))

        self.assertEqual(names, {"HTML", "CSS", "JavaScript"})

    def test_a_compound_and_its_own_fragment_are_never_emitted_together(self):
        for text in ("Wi-Fi", "CI/CD", "HTML/CSS", "Objective-C", "TCP/IP", "ETL/ELT", "On-Premise"):
            names = set(candidate_names(text, self.stopwords))
            for name in names:
                fragments = set(name.replace("/", "-").split("-"))
                self.assertFalse(
                    fragments & (names - {name}),
                    f"{text!r} produced both a compound and its fragment: {sorted(names)}",
                )

    def test_split_compound_resolves_nested_separators(self):
        self.assertEqual(split_compound("Java/Objective-C"), ("Java", "Objective-C"))
        self.assertEqual(split_compound("Wi-Fi"), ("Wi-Fi",))
        self.assertEqual(split_compound("Python"), ("Python",))


class SectionLabelTests(unittest.TestCase):
    def setUp(self):
        temp_dir, self.stopwords = _stopwords()
        self.addCleanup(temp_dir.cleanup)

    def test_candidates_inside_a_technology_list_are_labelled_section(self):
        text = "주요업무 Redis 운영 기술 스택 Java, Spring"
        sources = {candidate.name: candidate.source for candidate in extract_candidates(text, self.stopwords)}

        self.assertEqual(sources["Java"], "section")
        self.assertEqual(sources["Spring"], "section")
        self.assertEqual(sources["Redis"], "body")

    def test_empty_text_yields_no_candidates(self):
        self.assertEqual(extract_candidates("", self.stopwords), ())


class KoreanSpellingTests(unittest.TestCase):
    """Korean names are found by closed-list lookup, longest spelling first."""

    @classmethod
    def setUpClass(cls):
        cls.korean = load_korean_spellings(Path(__file__).resolve().parents[1] / "configs" / "tech_dictionary_korean.json")

    def setUp(self):
        temp_dir, self.stopwords = _stopwords()
        self.addCleanup(temp_dir.cleanup)

    def _names(self, text):
        return set(candidate_names(text, self.stopwords, self.korean))

    def test_the_longest_spelling_wins_so_자바스크립트_is_not_자바(self):
        self.assertEqual(self._names("자바스크립트"), {"자바스크립트"})

    def test_a_longer_spelling_consumes_its_span(self):
        self.assertEqual(self._names("리액트 네이티브 경험"), {"리액트 네이티브"})
        self.assertEqual(self._names("생성형 인공지능 모델"), {"생성형 인공지능"})

    def test_separate_occurrences_are_still_reported_separately(self):
        self.assertEqual(self._names("자바스크립트 와 자바 둘 다"), {"자바스크립트", "자바"})

    def test_a_spelling_inside_a_longer_hangul_run_does_not_count(self):
        # 뷰 in 코드 리뷰, 루비 in 그루비, 장고 in 냉장고, 지라 in 할지라도,
        # 러스트 in 일러스트, 깃 in 깃허브: all rejected by the boundary rule.
        self.assertEqual(self._names("코드 리뷰 진행"), set())
        self.assertEqual(self._names("그루비 스크립트"), set())
        self.assertEqual(self._names("냉장고 유지보수"), set())
        self.assertEqual(self._names("할지라도"), set())
        self.assertEqual(self._names("일러스트 작업"), set())

    def test_registered_spellings_are_found_at_a_boundary(self):
        self.assertEqual(self._names("파이썬, 자바, 쿠버네티스"), {"파이썬", "자바", "쿠버네티스"})
        self.assertEqual(self._names("딥러닝/머신러닝 경험"), {"딥러닝", "머신러닝"})
        self.assertEqual(self._names("깃허브 사용"), {"깃허브"})

    def test_unregistered_hangul_is_not_tokenised(self):
        # No open Hangul tokenisation: ordinary Korean words never become candidates.
        self.assertEqual(self._names("우대사항 협업 능력 커뮤니케이션"), set())

    def test_latin_and_korean_spellings_coexist(self):
        self.assertEqual(self._names("Python 과 파이썬 혼용"), {"Python", "파이썬"})

    def test_korean_extraction_is_off_unless_spellings_are_passed(self):
        self.assertEqual(set(candidate_names("파이썬", self.stopwords)), set())
