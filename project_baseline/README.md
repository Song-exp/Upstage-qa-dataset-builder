# 📘 [Upstage] AI Agent QA 시나리오 데이터셋 구축 베이스라인

본 프로젝트는 **한국 Public API**를 활용하여 도구를 적절히 활용하는 AI Agent 시나리오 데이터셋을 구축하는 베이스라인 코드입니다.

## 🎯 프로젝트 개요

### 최종 데이터셋 구성

| 조합   | Turn        | Tool 사용      | 최소 개수 |
| ------ | ----------- | -------------- | --------- |
| 조합 1 | Single-turn | Multi-tool-use | 2개 ㄴ    |
| 조합 2 | Multi-turn  | Multi-tool-use | 2개       |

**총 최소**: 4개 시나리오

## 📁 프로젝트 구조

```
sample_data/                 # 샘플 데이터
├── toolcall_single_turn_multi_tool_sample.json
├── toolcall_single_turn_multi_tool_sample_kr.json
├── toolcall_multi_turn_multi_tool_sample.json
└── toolcall_multi_turn_multi_tool_sample_kr.json

project_baseline/
├── baseline_code.ipynb          # 메인 실행 코드 (Jupyter Notebook)
├── requirements.txt              # Python 의존성 패키지
├── test_think_tag.py            # Think 태그 포함 여부 테스트 스크립트
│
├── eval/                        # 평가 모듈
│   └── evaluate.py              # BFCL 기준 평가 스크립트
│
├── data/                        # 생성된 시나리오 데이터
│   ├── defense_single_turn_solar.jsonl
│   └── defense_multi_turn_solar.jsonl
│
├── outputs/                     # 최종 데이터셋
│   ├── final_dataset.jsonl      # 정량평가 통과 시나리오 (JSONL)
│   └── final_dataset.json       # 데이터셋 + 통계 (JSON)
│
├── artifacts/                    # 평가 리포트
│   └── bfcl_evaluation_report.csv
```

## 🔧 설치 및 설정

### 1. 환경 설정

```bash
# Python 패키지 설치
pip install -r requirements.txt

# BFCL (Gorilla) editable 설치
pip install -e external/gorilla
```

### 2. API 키 설정

1. [Upstage Console](https://console.upstage.ai/) 접속
2. Dashboard > API Keys 메뉴에서 새 키 발급
3. `.env` 파일 생성 또는 코드에서 직접 설정:

```bash
# .env 파일 생성
echo "UPSTAGE_API_KEY=your_api_key_here" > .env
```

또는 `baseline_code.ipynb`의 Cell 4에서 직접 설정:

```python
UPSTAGE_API_KEY = "your_api_key_here"
```

## 🚀 프로젝트 진행 단계

#### 단계 1: 도메인 선정 및 Tool 정의

- 10개 도메인 중 1개 선택 (정부 & 공공기관, 게임 & 엔터테인먼트, 소셜 & 커뮤니케이션, 지도/위치, 네이버, 카카오, 쇼핑, 음식/의료, 날씨/환경, 미디어 & 콘텐츠)
- 최소 2개 이상의 독립적인 Tool 설계
- Public API 기반

#### 단계 2: QA 시나리오 데이터 구축

- **Single-turn & Multi-tool-use**: 최소 2개 생성
- **Multi-turn & Multi-tool-use**: 최소 2개 생성
- 

#### 단계 3: BFCL Rule Based 정량 평가

- 정량 평가: Correct Function Name, Valid Arguments, No Hallucinated Calls
- 평가 통과한 시나리오만 최종 데이터셋에 포함

#### 단계 4: 정성 평가

- 시나리오 적합성 (15점)
- 창의성 및 다양성 (15점)
- 구체성 (15점)
- 실행 가능성 (25점)
- 윤리·안전성 (10점)

### 📊 평가 기준

### 정량 평가 (BFCL 기준)

| 평가 항목                       | 설명                    | 방법       |
| ------------------------------- | ----------------------- | ---------- |
| **Correct Function Name** | 올바른 함수 호출 여부   | Rule-based |
| **Valid Arguments**       | 인자 타입/포맷 정확성   | Rule-based |
| **No Hallucinated Calls** | 정의되지 않은 함수 방지 | Rule-based |

### 정성 평가 기준

| 평가 항목                  | 배점 | 평가 기준                                                 |
| -------------------------- | ---- | --------------------------------------------------------- |
| **시나리오 적합성**  | 15   | 도메인/Task와 일관성, 실제 서비스/공공 API 활용 맥락 반영 |
| **창의성 및 다양성** | 15   | 새로운 활용 아이디어, 다양한 상황·조건 커버              |
| **구체성**           | 15   | 상황·조건 구체적 기술, 실제 API 호출 매핑 가능성         |
| **실행 가능성**      | 25   | LLM + 한국 API 기반 실제 실행 가능, 오류 복구 성공        |
| **윤리·안전성**     | 10   | 개인정보/민감 이슈 회피, AI 윤리 문제 없음                |

### 평가 비중

- **조합 1 (Single Turn & Multi Tool Use)**: 정량 50% + 정성 50%
- **조합 2 (Multi Turn & Multi Tool Use)**: 정량 30% + 정성 70%

## 📝 주요 파일 설명

### `baseline_code.ipynb`

메인 실행 코드로 다음 단계를 포함합니다:

- 환경 설정 및 라이브러리 설치
- Solar Pro 2 API 설정
- 도메인 선정 및 Tool 정의
- Single-turn 시나리오 생성
- Multi-turn 시나리오 생성
- BFCL 평가 실행
- 최종 데이터셋 저장

### `eval/evaluate.py`

BFCL 기준 평가를 수행하는 모듈:

- `evaluate_entry()`: 단일 항목 평가
- `evaluate_turn()`: 단일 턴 평가
- `evaluate_single_tool_call()`: 단일 도구 호출 평가
- `load_data()`: 데이터 로드 (JSON/JSONL)

## 📄 Output

- **JSONL**: `outputs/final_dataset.jsonl` - 정량평가 통과 시나리오
- **JSON**: `outputs/final_dataset.json` - 데이터셋 + 통계 정보
- **CSV**: `artifacts/bfcl_evaluation_report.csv` - 평가 리포트

## 📚 참고 자료

- [활용 데이터: Public API](https://github.com/yybmion/public-apis-4Kr)
- [BFCL 리더보드](https://github.com/ShishirPatil/gorilla)
- [Nemotron 시나리오 데이터](https://huggingface.co/datasets/nvidia/Nemotron-Post-Training-Dataset-v1)
- [Upstage Console](https://developers.upstage.ai/)

## ⚠️ 주의사항

1. **API 키 보안**: API 키를 코드에 직접 입력하지 말고 `.env` 파일 사용 권장
2. **Think 태그**: Assistant 응답에 `<think>...</think>` 태그가 반드시 포함되어야 함
3. **데이터 형식**: 모든 시나리오는 JSONL 형식으로 저장되며, 정량 평가 통과 항목만 최종 데이터셋에 포함

## 🛠️ 의존성 패키지

```
python-dotenv>=1.0.1
requests>=2.32.3
tqdm>=4.66.5
rich>=13.8.1
pandas>=2.2.2
numpy>=1.26.4
datasets>=2.21.0
huggingface-hub>=0.24.6
```

## 📝 라이선스

© 2025 Upstage Co., Ltd. All rights reserved.

 본 교육용 코드 및 자료의 모든 지식재산권은 업스테이지(Upstage Co., Ltd.)에 귀속됩니다. 본 콘텐츠를 사전 서면 동의 없이 **외부로 유출, 복제, 수정, 배포, 게시하는 행위는 엄격히 금지**됩니다.
