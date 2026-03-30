# TOSG-400M Pattern Signal Viewer — 요구사항 문서

> 버전: v3.0  
> 최종 수정일: 2026-03-31

---

## 1. 개요

**TOSG-400M Pattern Signal Viewer**는 디스플레이 패널 구동용 타이밍 컨트롤러(TOSG-400M)의
OTD(Output Timing Definition) 파일을 읽고, 신호 파형을 시각화하며, 편집 및 내보내기를 지원하는
데스크탑 GUI 애플리케이션입니다.

---

## 2. 사용 환경

| 항목 | 사양 |
|------|------|
| 운영체제 | Windows 10/11, macOS 12 이상 |
| Python | 3.9 이상 |
| 필수 라이브러리 | tkinter (내장), matplotlib, openpyxl |

---

## 3. 주요 기능 요구사항

### 3.1 파일 불러오기

| ID | 기능 | 설명 |
|----|------|------|
| F-01 | OTD 파일 불러오기 | `.otd` 파일 파싱 후 전체 모델을 좌측 모델 목록에 표시 |
| F-02 | Excel 파일 불러오기 | `.xlsx` 파일(양식 호환)을 파싱하여 모델 목록에 표시 |
| F-03 | 다중 모델 지원 | OTD/Excel의 복수 모델(시트) 동시 로드 |
| F-04 | MULTIREMOTE 불러오기 | OTD의 MULTIREMOTE 섹션(500/600번대) 파싱 및 표시 |

### 3.2 파일 내보내기

| ID | 기능 | 설명 |
|----|------|------|
| F-10 | OTD 파일 내보내기 | 전체 모델/신호/패턴/MULTIREMOTE를 OTD 포맷으로 저장 |
| F-11 | OTD 섹션 태그 | `[HEADER]`, `[MODEL_XXX]`, `[SIGNAL_DATA_XXX]`, `[PATTERN_DATA_XXX]` 태그 포함 |
| F-12 | Excel 파형 출력 | 신호 파형을 셀 테두리로 시각화, edge 구간 위에 `↔ Xus` timing 표시 |
| F-13 | Excel 데이터 출력 | 신호 파라미터를 Excel 불러오기 양식 호환 형식으로 저장 |
| F-14 | 포맷 파일 생성 | Excel 불러오기에 사용하는 빈 양식 `.xlsx` 파일 생성 |

### 3.3 UI 레이아웃

| ID | 기능 | 설명 |
|----|------|------|
| U-01 | 좌측 모델 목록 | 불러온 모든 모델을 Listbox로 표시, 클릭 시 신호/패턴 갱신 |
| U-02 | 신호 편집 탭 | 신호 파라미터 표(Treeview) + 인라인 편집 폼 |
| U-03 | 패턴 데이터 탭 | 패턴 전압 데이터(R/G/B/W V1~V4) 표시 |
| U-04 | MULTIREMOTE 탭 | MRT 그룹 목록 및 구동 순서 편집 |
| U-05 | 타이밍 다이어그램 | matplotlib 기반 파형 시각화 (우측 패널) |
| U-06 | 상태 표시줄 | 현재 모델, 신호 수, 패턴 수, MULTIREMOTE 수 표시 |

### 3.4 신호 편집

| ID | 기능 | 설명 |
|----|------|------|
| E-01 | 신호 추가 | 폼 입력 후 "신호 추가" 클릭 → SignalManager 및 ModelStore 동기화 |
| E-02 | 신호 수정 | 목록에서 신호 선택 후 "신호 수정" 클릭 → 수정 반영 |
| E-03 | 신호 삭제 | 선택 신호 삭제 |
| E-04 | 신호 복제 | 선택 신호 복사본 추가 |
| E-05 | 신호 순서 변경 | ↑/↓ 버튼으로 목록 내 순서 변경 |
| E-06 | 신호 가시성 | Visible 열 클릭으로 파형 표시/숨김 토글 |

### 3.5 뷰 제어

| ID | 기능 | 설명 |
|----|------|------|
| V-01 | 프레임 수 | 표시할 반복 프레임 수 조절 (1~10) |
| V-02 | X축 모드 | Frame 기준 / Time(us) 기준 전환 |
| V-03 | 뷰 시간 | X축 최대값 제한 (us) |
| V-04 | 그리드 | 타이밍 다이어그램 그리드 표시/숨김 |
| V-05 | 뷰 모드 | 개별 보기 / 합쳐 보기 전환 |
| V-06 | 범례 위치 | 합쳐 보기 시 범례 위치 선택 |

---

## 4. OTD 파일 포맷

### 4.1 구조

```
[HEADER]
1001=DEVICE,LCD SHORTING BAR
1002=NAME,TOSG-400M
...
1010=CURRENT_MODEL_NUMBER,2

[MODEL_001]
101=MODEL,001
102=NAME,모델이름
103=SYNCDATA,166667
104=SYNCCNTR,0

[SIGNAL_DATA_001]
201-S01=GND,0,0,0,0,0,0,0,0,0,0,0,0,0
...

[PATTERN_DATA_001]
401=PTN01,VGL-10,-10000,18000,0,0,...
...
999=END-MODEL_001

[GLOBAL_MRT]
52=GLOBAL_MRT,001,B6-250916-T

[MULTIREMOTE_001]
501=MRT,001,B6-250916-T
601=MRT01,8,1,0
...

9999=END
```

### 4.2 단위

| 데이터 | OTD 단위 | 앱 내부 단위 |
|--------|----------|-------------|
| 전압 | mV | V |
| 시간 | 1/10 us | us |
| 주파수 | 계산 (10,000,000 / SYNCDATA) | Hz |

---

## 5. Excel 파일 포맷 (불러오기/내보내기 공통)

### 5.1 신호 데이터 영역 (시트 내 1~37행)

| 열 | 내용 | 단위 |
|----|------|------|
| A | NUM (S01~S36) | - |
| B | NAME | - |
| C | SIG TYPE | - |
| D | SIG MODE | 0/1 |
| E | INV | 0/1 |
| F | V1 | V |
| G | V2 | V |
| H | V3 | V |
| I | V4 | V |
| J | DELAY | us |
| K | PERIOD | us |
| L | WIDTH | us |
| M | LENGTH | us |
| N | AREA | us |

### 5.2 SyncData 영역 (P/Q열, 2~4행)

| 행 | P열 | Q열 |
|----|-----|-----|
| 2 | SyncData (us) | 값 |
| 3 | Frequency (Hz) | 값 |
| 4 | SyncCounter | 값 |

### 5.3 패턴 데이터 영역 (39행~)

- 39행: `=== PATTERN DATA ===` 구분자
- 40행: 헤더 (PTN_NO, NAME, R_V1~R_V4, G_V1~G_V4, B_V1~B_V4, W_V1~W_V4, TYPE)
- 41행~: 패턴 데이터

---

## 6. 파일 구성 (src 폴더)

| 파일 | 역할 |
|------|------|
| `model_store.py` | 다중 모델 데이터 저장소 (ModelStore, ModelData, MultiRemoteGroup) |
| `model_list_panel.py` | 좌측 모델 목록 UI 패널 |
| `signal_model.py` | Signal 클래스 및 SignalManager |
| `signal_table_widget.py` | 신호 목록 Treeview 위젯 |
| `signal_editor_panel.py` | 인라인 신호 편집 폼 |
| `pattern_data_panel.py` | 패턴 데이터 표시 패널 |
| `multiremote_panel.py` | MULTIREMOTE 편집 패널 |
| `control_panel.py` | 상단 제어 패널 (I/O 버튼, 뷰 제어) |
| `timing_viewer.py` | 타이밍 다이어그램 (matplotlib) |
| `otd_parser.py` | OTD 파일 파서 |
| `otd_exporter.py` | OTD 파일 내보내기 |
| `otd_to_model_store.py` | OtdFile → ModelStore 변환 |
| `excel_importer.py` | Excel 파일 불러오기 |
| `excel_waveform_exporter.py` | Excel 파형 시각화 내보내기 |
| `excel_format_generator.py` | Excel 빈 양식 파일 생성 |
| `sync_data.py` | SyncData/주파수 관리 |
| `signal_storage.py` | 신호 JSON 저장/불러오기 |
| `waveform_generator.py` | 파형 데이터 생성 |

---

## 7. 비기능 요구사항

- **응답성**: 대형 OTD 파일(36신호 × 10모델) 불러오기 5초 이내
- **호환성**: openpyxl 3.x 버전 호환
- **코드 품질**: 모든 public 메서드에 한국어 docstring 작성
