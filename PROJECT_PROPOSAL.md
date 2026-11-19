# Project Proposal

## Team Information

- **Team Name:** JOBGUTS
- **Team Leader:** 서동균 (2021270664)
- **Team Members:**
  - 김경선 (2022270656)
  - 정비호 (2022270622)
  - 설경민 (2022270643)

## Project Title

**Analysis of Technology Combinations in Korean IT Job Postings**

## Project Description (English)

This project analyzes the technology combinations that frequently appear together in Korean IT job postings and helps users discover related skills to prepare for their target roles. We will use a public dataset of Korean IT job advertisements, treating each posting as a transaction and each required technology as an item. After standardizing inconsistent technology names such as “JS,” “JavaScript,” and “자바스크립트,” we will apply Apriori and association-rule mining to compare frequent itemsets and rules before and after normalization. The service will present role-specific technology combinations, personalized related-skill recommendations, a technology relationship graph, and supporting job-posting excerpts with confidence and interest values.

## 프로젝트 설명 (한국어)

이 프로젝트는 국내 IT 채용공고에서 자주 함께 등장하는 기술 조합을 분석하고, 사용자가 목표 직무를 준비할 때 함께 학습할 만한 연관 기술을 찾도록 돕는다. 공개 한국 IT 채용공고 데이터셋을 활용하여 채용공고 하나를 장바구니, 요구 기술 하나를 항목으로 보고 분석한다. “JS”, “JavaScript”, “자바스크립트”처럼 표기가 다른 기술명을 표준화한 뒤, 정규화 전후의 빈발 항목집합과 Apriori 기반 연관규칙을 비교한다. 결과물로 직무별 기술 조합, 보유 기술 기반 추천 목록, 기술 연결 그래프, 그리고 confidence·interest 값과 실제 공고 문장을 포함한 추천 근거를 제공한다.

## GitHub Repository URL

- **URL:** https://github.com/k0ng-min/2026_bigdata_JobGuts

## Team Roles

| Member | Student ID | Role | Responsibilities |
| --- | --- | --- | --- |
| 서동균 | 2021270664 | Team Leader | 일정 조율, 통합 검토, 발표 자료 정리 |
| 김경선 | 2022270656 | 데이터·정규화 | 데이터 품질 점검, 기술명 사전 및 정규화 검증 |
| 정비호 | 2022270622 | 연관규칙 분석 | Apriori 실험, 지표 비교, 세그먼트 분석 |
| 설경민 | 2022270643 | 서비스·시각화 | 근거 공고 조회, CLI·화면, 결과 시각화 |
