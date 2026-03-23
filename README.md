# TOSG-400M Pattern Signal Viewer

TOSG-400M 패턴 생성기로 만든 신호를 시각화하는 Python 프로그램입니다.

## 기능

- ✅ 신호 추가/수정/삭제
- ✅ 타이밍 다이어그램 시각화
- ✅ 프레임 수 조절 (1~10 프레임)
- ✅ 모델별 신호 저장/불러오기
- ✅ SyncData 자동 계산 (1/주파수)
- ✅ SIG MODE 기반 파형 생성

## 설치

```bash
pip install -r requirements.txt
```

## 실행

```bash
python main.py
```

## 사용법

### 1. 신호 추가
- "신호 추가" 버튼 클릭
- 신호 파라미터 입력:
  - 신호 이름
  - SIG MODE (0 또는 1)
  - INVERSION (0 또는 1)
  - V1, V2, V3, V4 (전압, V 단위)
  - DELAY, WIDTH, PERIOD (길이, μm 단위)

### 2. SIG MODE 설명

#### 일반 모드 (Delay, Width, Period > 0)
- **MODE=0, INV=0**: V1,V2 사용, Frame별 반전 없음
- **MODE=0, INV=1**: V1,V2 사용, Frame별 반전 적용
- **MODE=1, INV=0**: Odd Frame은 V1,V2, Even Frame은 V3,V4
- **MODE=1, INV=1**: Odd Frame은 V1,V2, Even Frame은 V4,V3

#### DC 모드 (Delay=0, Width=0, Period=0)
- **MODE=0, INV=0**: V1 DC 출력
- **MODE=0, INV=1**: Frame별 V1, V2 반복
- **MODE=1, INV=0**: Frame별 V1, V3 반복
- **MODE=1, INV=1**: Frame별 V1, V4 반복

### 3. 모델 및 주파수 선택
- 제어 패널에서 모델 선택
- 주파수 선택 (SyncData 자동 계산)

### 4. 프레임 조절
- 프레임 수 스핀박스에서 1~10 선택
- 타이밍 다이어그램에 자동 반영

### 5. 저장/불러오기
- "저장" 버튼: 현재 모델의 신호 저장
- "불러오기" 버튼: 모델별 저장된 신호 불러오기
- 데이터는 `signal_data/` 디렉토리에 JSON 형식으로 저장

## 파일 구조

```
tosg-pattern-viewer/
├── main.py                    # 메인 애플리케이션
├── signal_model.py            # 신호 데이터 모델
├── sync_data.py               # SyncData 관리
├── signal_storage.py          # 신호 저장/로드
├── waveform_generator.py      # 파형 생성
├── timing_viewer.py           # 타이밍 다이어그램 뷰어
├── signal_table_widget.py     # 신호 테이블 위젯
├── signal_dialog.py           # 신호 편집 다이얼로그
├── control_panel.py           # 제어 패널
├── requirements.txt           # 필요 라이브러리
├── models_config.json         # 모델 설정 (자동 생성)
└── signal_data/               # 신호 데이터 저장 디렉토리 (자동 생성)
```

## 기술 스택

- **GUI**: Tkinter (Python 기본 내장)
- **시각화**: Matplotlib
- **수치 계산**: NumPy

## 라이센스

MIT License
