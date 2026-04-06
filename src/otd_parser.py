"""
OTD 파일 파서 모듈
TOSG-400M OTD 파일 포맷을 파싱하여 Python 데이터 구조로 변환합니다.

OTD 파일 구조:
  - HEADER (1000번대): 장비 기본 정보
  - MODEL (100번대): 모델 정보 (주파수, SyncData 등)
  - SIGNAL_DATA (200번대): 신호 파라미터 (전압 mV, 시간 1/10us)
  - PATTERN_DATA (400번대): 패턴 전압 데이터 (R/G/B/W V1-V4, mV → V)
  - GLOBAL_MRT (52=): 멀티 원격 그룹 목록
  - MULTIREMOTE (500/600번대): 멀티 원격 데이터 및 순서
  - 999=END: 모델 종료 또는 MULTIREMOTE 종료
  - 9999=END: 전체 종료
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict


# ────────────────────────────────────────────────────────────────
# 데이터 클래스
# ────────────────────────────────────────────────────────────────

@dataclass
class OtdHeader:
    """OTD 파일 헤더 (1000번대) 데이터"""
    device: str = ""            # 1001=DEVICE
    name: str = ""              # 1002=NAME
    pg_version: str = ""        # 1003=PG_VERSION
    feature: str = ""           # 1004=FEATURE
    filesystem: str = ""        # 1005=FILESYSTEM
    compatibility: str = ""     # 1006=COMPATIBILITY
    filetype: str = ""          # 1007=FILETYPE
    option1: str = ""           # 1008=OPTION1
    option2: str = ""           # 1009=OPTION2
    model_number: str = ""      # 1010=CURRENT.MODEL_NUMBER
    group_number: str = ""      # 1011=CURRENT_GROUP NUMBER


@dataclass
class OtdSignal:
    """SIGNAL_DATA (200번대) 단일 신호 데이터
    
    OTD 원본 단위: 전압=mV, 시간=1/10us
    파서 출력 단위: 전압=V, 시간=us
    """
    num: str = ""           # S01~S32
    name: str = ""          # 신호 이름
    v1: float = 0.0         # V (mV → V 변환)
    v2: float = 0.0
    v3: float = 0.0
    v4: float = 0.0
    delay: float = 0.0      # us (1/10us → us 변환)
    width: float = 0.0      # us
    period: float = 0.0     # us
    length: float = 0.0     # us
    area: float = 0.0       # us
    mf: str = "0"
    mod: str = "0"
    inv: str = "0"          # INVERSION
    sig_type: int = 0       # 0=NONE,1=CLK,2=REF,3=RED,4=GREEN,5=BLUE
    color: str = "#0000FF"


@dataclass
class OtdPattern:
    """PATTERN_DATA (400번대) 단일 패턴 데이터
    
    OTD 원본 단위: 전압=mV
    파서 출력 단위: 전압=V
    """
    ptn_no: int = 0         # PTN 번호 (1부터)
    name: str = ""
    r_v1: float = 0.0       # R 채널 V1~V4 (V)
    r_v2: float = 0.0
    r_v3: float = 0.0
    r_v4: float = 0.0
    g_v1: float = 0.0       # G 채널
    g_v2: float = 0.0
    g_v3: float = 0.0
    g_v4: float = 0.0
    b_v1: float = 0.0       # B 채널
    b_v2: float = 0.0
    b_v3: float = 0.0
    b_v4: float = 0.0
    w_v1: float = 0.0       # W 채널
    w_v2: float = 0.0
    w_v3: float = 0.0
    w_v4: float = 0.0
    ptn_type: int = 0       # 0=없음,1=A,2=B,3=PF1,4=PF2,5=PF3,6=ZIV,7=ZRB,...


@dataclass
class OtdModel:
    """하나의 MODEL 블록 전체 데이터"""
    model_num: str = ""         # 모델 번호 (예: "010")
    name: str = ""              # 모델 이름
    sync_data_raw: int = 0      # SYNCDATA 원본값 (단위: 1/10us)
    sync_freq_hz: float = 0.0   # 계산된 주파수 (Hz) = 10_000_000 / sync_data_raw
    sync_data_us: float = 0.0   # 1프레임 길이 (us) = sync_data_raw / 10
    sync_cntr: int = 0          # SYNCCNTR
    signals: List[OtdSignal] = field(default_factory=list)
    patterns: List[OtdPattern] = field(default_factory=list)


@dataclass
class MultiRemoteEntry:
    """멀티 리모트 단일 실행 항목 (600번대)"""
    order: int = 0
    model_num: int = 0
    pattern_num: int = 0
    time: float = 0.0


@dataclass
class MultiRemote:
    """멀티 원격 데이터 (500/600번대) 블록"""
    mrt_id: str = ""        # MRT ID (001, 002, ...)
    name: str = ""
    entries: List[MultiRemoteEntry] = field(default_factory=list)


@dataclass
class OtdFile:
    """OTD 파일 전체 파싱 결과"""
    header: OtdHeader = field(default_factory=OtdHeader)
    models: List[OtdModel] = field(default_factory=list)
    global_mrt_groups: List[str] = field(default_factory=list)
    multi_remotes: List[MultiRemote] = field(default_factory=list)
    filepath: str = ""

    def get_model(self, model_num: str) -> Optional[OtdModel]:
        """모델 번호로 모델 검색"""
        for m in self.models:
            if m.model_num == model_num:
                return m
        return None


# ────────────────────────────────────────────────────────────────
# 파서
# ────────────────────────────────────────────────────────────────

# SIGNAL TYPE 매핑
SIGNAL_TYPE_MAP = {0: 'NONE', 1: 'CLK', 2: 'REF', 3: 'RED', 4: 'GREEN', 5: 'BLUE'}

# PATTERN TYPE 매핑
PATTERN_TYPE_MAP = {
    0: '-', 1: 'A', 2: 'B', 3: 'PF1', 4: 'PF2', 5: 'PF3',
    6: 'ZIV', 7: 'ZRB', 8: 'ZRB2', 9: 'ZRB3', 10: 'MUX4D', 11: 'MUX1D'
}


def _mv_to_v(mv_str: str) -> float:
    """mV 문자열을 V(float)로 변환"""
    try:
        return float(mv_str) / 1000.0
    except (ValueError, TypeError):
        return 0.0


def _tenth_us_to_us(raw_str: str) -> float:
    """1/10us 단위 문자열을 us(float)로 변환"""
    try:
        return float(raw_str) / 10.0
    except (ValueError, TypeError):
        return 0.0


class OtdParser:
    """
    OTD 파일 파서 클래스
    
    parse() 메서드로 OTD 파일을 읽어 OtdFile 객체 반환.

    주의사항:
      - 섹션 태그([MODEL_XXX], [SIGNAL_DATA_XXX], [PATTERN_DATA_XXX],
        [HEADER], [GLOBAL_MRT], [MULTIREMOTE_XXX])는 '='가 없어
        기존 key=value 파싱으로는 처리 불가. 별도 섹션 태그 파싱 로직 필요.
      - MULTIREMOTE 데이터(600번대)는 섹션 태그를 통해 current_mrt를
        초기화한 뒤에만 올바르게 연결됨.
    """

    # 파서 내부 상태 상수
    _STATE_HEADER       = 'header'
    _STATE_MODEL        = 'model'
    _STATE_GLOBAL_MRT   = 'global_mrt'
    _STATE_MULTIREMOTE  = 'multiremote'

    @staticmethod
    def parse(filepath: str) -> OtdFile:
        """
        OTD 파일을 파싱하여 OtdFile 객체 반환
        
        Args:
            filepath: OTD 파일 경로
            
        Returns:
            OtdFile: 파싱된 데이터 객체
            
        Raises:
            FileNotFoundError: 파일을 찾을 수 없을 때
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {filepath}")

        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        result = OtdFile(filepath=filepath)
        current_model: Optional[OtdModel] = None
        current_mrt: Optional[MultiRemote] = None
        in_global_mrt = False

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            # ── 섹션 태그 처리 [ ... ] ──────────────────────────
            # 섹션 태그는 '='를 포함하지 않으므로 먼저 처리
            if line.startswith('[') and line.endswith(']'):
                tag = line[1:-1]  # 괄호 제거

                if tag == 'HEADER':
                    in_global_mrt = False
                    current_model = None
                    current_mrt = None

                elif tag == 'GLOBAL_MRT':
                    in_global_mrt = True
                    # 현재 열린 모델 닫기
                    if current_model is not None:
                        result.models.append(current_model)
                        current_model = None

                elif tag.startswith('MODEL_'):
                    # [MODEL_XXX] 태그: 새 모델 시작 신호
                    # 실제 모델 번호는 아래 101=MODEL 라인에서 읽음
                    # (단, 여기서 current_model을 초기화해두지 않음 — 101= 발견 시 초기화)
                    in_global_mrt = False

                elif tag.startswith('SIGNAL_DATA_') or tag.startswith('PATTERN_DATA_'):
                    # 섹션 구분 태그 — 파싱 상태 변경 불필요 (key_num으로 자동 처리)
                    pass

                elif tag.startswith('MULTIREMOTE_'):
                    # [MULTIREMOTE_XXX] 태그: 새 MultiRemote 블록 시작
                    # ★ 버그 수정: 이 태그를 인식해야 600번대 데이터가 current_mrt에 연결됨
                    in_global_mrt = False
                    # 현재 열린 모델 닫기
                    if current_model is not None:
                        result.models.append(current_model)
                        current_model = None
                    # 새 MultiRemote 객체 준비 (이름은 501= 라인에서 설정)
                    current_mrt = MultiRemote()
                    result.multi_remotes.append(current_mrt)

                continue  # 섹션 태그 라인은 key=value 파싱 불필요

            # ── 전체/모델 종료 ──────────────────────────────────
            if line == '9999=END':
                break

            if line.startswith('999=END'):
                # 모델 종료 또는 MULTIREMOTE 블록 종료
                if current_model is not None:
                    result.models.append(current_model)
                    current_model = None
                if in_global_mrt:
                    in_global_mrt = False
                # MULTIREMOTE 블록 종료 — current_mrt는 유지(이미 result에 추가됨)
                # 다음 [MULTIREMOTE_XXX] 태그에서 새로 시작됨
                continue

            # ── 키=값 파싱 ─────────────────────────────────────
            if '=' not in line:
                continue
            key_raw, _, value_raw = line.partition('=')
            key = key_raw.strip()
            value = value_raw.strip()

            try:
                key_num = int(key)
            except ValueError:
                key_num = None

            # ── GLOBAL_MRT 식별 (52=...) ──────────────────────
            if key == '52':
                in_global_mrt = True
                result.global_mrt_groups.append(value)
                continue

            if key_num is None:
                continue

            # ── HEADER (1000번대) ──────────────────────────────
            if 1000 <= key_num < 2000:
                OtdParser._parse_header_line(key_num, value, result.header)
                continue

            # ── 모델 시작 (101=MODEL,...) ──────────────────────
            if key_num == 101:
                current_model = OtdModel()
                parts = value.split(',')
                # "MODEL,010" 또는 "010" 형식 모두 처리
                current_model.model_num = parts[-1].strip() if parts else value
                continue

            # ── MULTIREMOTE 영역 (current_model이 없을 때) ────
            if current_model is None:
                if 500 <= key_num < 600:
                    # 501=MRT,001,이름 형식
                    # [MULTIREMOTE_XXX] 태그에서 이미 current_mrt 생성됨
                    if current_mrt is None:
                        # 섹션 태그 없이 501=이 먼저 올 경우 대비
                        current_mrt = MultiRemote()
                        result.multi_remotes.append(current_mrt)
                    parts = [p.strip() for p in value.split(',')]
                    # parts: ['MRT', '001', '이름'] 또는 ['001', '이름']
                    if len(parts) >= 3 and parts[0].upper() == 'MRT':
                        current_mrt.mrt_id = parts[1]
                        current_mrt.name   = parts[2]
                    elif len(parts) >= 2:
                        current_mrt.mrt_id = parts[0]
                        current_mrt.name   = parts[1]
                    elif len(parts) >= 1:
                        current_mrt.mrt_id = parts[0]

                elif 600 <= key_num < 700:
                    # 601=MRT01,모델번호,패턴번호,시간
                    # ★ 버그 수정: current_mrt가 None이면 마지막 것을 사용
                    if current_mrt is None and result.multi_remotes:
                        current_mrt = result.multi_remotes[-1]

                    if current_mrt is not None:
                        parts = [p.strip() for p in value.split(',')]
                        # parts: ['MRT01', '8', '1', '0']
                        # MRT01 접두사를 제거하고 데이터만 파싱
                        data_parts = parts[1:] if (len(parts) > 1 and
                                                   parts[0].upper().startswith('MRT')) else parts
                        entry = MultiRemoteEntry()
                        try:
                            entry.order       = key_num - 600  # 601 → 1, 602 → 2 ...
                            entry.model_num   = int(data_parts[0]) if len(data_parts) > 0 else 0
                            entry.pattern_num = int(data_parts[1]) if len(data_parts) > 1 else 0
                            entry.time        = float(data_parts[2]) if len(data_parts) > 2 else 0.0
                        except (ValueError, IndexError):
                            pass
                        current_mrt.entries.append(entry)
                continue

            # ── 모델 내 데이터 ────────────────────────────────
            if key_num == 102:
                # NAME
                parts = value.split(',', 1)
                current_model.name = parts[-1].strip() if len(parts) > 1 else value

            elif key_num == 103:
                # SYNCDATA (1/10us)
                parts = value.split(',')
                raw = parts[-1].strip()
                try:
                    current_model.sync_data_raw = int(raw)
                    current_model.sync_data_us = current_model.sync_data_raw / 10.0
                    if current_model.sync_data_raw > 0:
                        current_model.sync_freq_hz = 10_000_000.0 / current_model.sync_data_raw
                except ValueError:
                    pass

            elif key_num == 104:
                # SYNCCNTR
                parts = value.split(',')
                try:
                    current_model.sync_cntr = int(parts[-1].strip())
                except ValueError:
                    pass

            # ── SIGNAL_DATA (200번대) ─────────────────────────
            elif 201 <= key_num < 300:
                signal = OtdParser._parse_signal_line(key_num, value)
                if signal:
                    current_model.signals.append(signal)

            # ── PATTERN_DATA (400번대) ─────────────────────────
            elif 401 <= key_num < 500:
                pattern = OtdParser._parse_pattern_line(key_num, value)
                if pattern:
                    current_model.patterns.append(pattern)

        # 파일 끝까지 읽었는데 모델이 아직 열려있는 경우
        if current_model is not None:
            result.models.append(current_model)

        return result

    @staticmethod
    def _parse_header_line(key_num: int, value: str, header: OtdHeader):
        """헤더 라인 파싱"""
        parts = value.split(',', 1)
        actual_value = parts[1].strip() if len(parts) > 1 else value.strip()

        mapping = {
            1001: 'device',
            1002: 'name',
            1003: 'pg_version',
            1004: 'feature',
            1005: 'filesystem',
            1006: 'compatibility',
            1007: 'filetype',
            1008: 'option1',
            1009: 'option2',
            1010: 'model_number',
            1011: 'group_number',
        }
        attr = mapping.get(key_num)
        if attr:
            setattr(header, attr, actual_value)

    @staticmethod
    def _parse_signal_line(key_num: int, value: str) -> Optional[OtdSignal]:
        """
        SIGNAL_DATA 라인 파싱
        
        포맷: 201-S01=GND,0,0,0,0,0,0,0,0,0,0,0,0,0
        컬럼 (value 기준): NUM, NAME, V1, V2, V3, V4, DELAY, WIDTH, PERIOD, LENGTH, AREA, MF, MOD, INV, [TYPE]
        단위: 전압=mV, 시간=1/10us
        """
        parts = [p.strip() for p in value.split(',')]
        if len(parts) < 2:
            return None

        sig = OtdSignal()
        sig.num  = parts[0]  # S01
        sig.name = parts[1] if len(parts) > 1 else ""

        # 전압 (mV → V)
        sig.v1 = _mv_to_v(parts[2]) if len(parts) > 2 else 0.0
        sig.v2 = _mv_to_v(parts[3]) if len(parts) > 3 else 0.0
        sig.v3 = _mv_to_v(parts[4]) if len(parts) > 4 else 0.0
        sig.v4 = _mv_to_v(parts[5]) if len(parts) > 5 else 0.0

        # 시간 (1/10us → us)
        sig.delay  = _tenth_us_to_us(parts[6])  if len(parts) > 6  else 0.0
        sig.width  = _tenth_us_to_us(parts[7])  if len(parts) > 7  else 0.0
        sig.period = _tenth_us_to_us(parts[8])  if len(parts) > 8  else 0.0
        sig.length = _tenth_us_to_us(parts[9])  if len(parts) > 9  else 0.0
        sig.area   = _tenth_us_to_us(parts[10]) if len(parts) > 10 else 0.0

        sig.mf  = parts[11] if len(parts) > 11 else "0"
        sig.mod = parts[12] if len(parts) > 12 else "0"
        sig.inv = parts[13] if len(parts) > 13 else "0"

        try:
            sig.sig_type = int(parts[14]) if len(parts) > 14 else 0
        except ValueError:
            sig.sig_type = 0

        return sig

    @staticmethod
    def _parse_pattern_line(key_num: int, value: str) -> Optional[OtdPattern]:
        """
        PATTERN_DATA 라인 파싱
        
        포맷: 401=PTN01,NAME,R_V1..V4,G_V1..V4,B_V1..V4,W_V1..V4,TYPE
        단위: 전압=mV
        """
        parts = [p.strip() for p in value.split(',')]
        if len(parts) < 2:
            return None

        ptn = OtdPattern()
        ptn_num_str = parts[0]  # 예: PTN01
        try:
            ptn.ptn_no = int(''.join(filter(str.isdigit, ptn_num_str)))
        except ValueError:
            ptn.ptn_no = key_num - 400

        ptn.name = parts[1] if len(parts) > 1 else ""

        # R V1~V4 (mV → V)
        ptn.r_v1 = _mv_to_v(parts[2])  if len(parts) > 2  else 0.0
        ptn.r_v2 = _mv_to_v(parts[3])  if len(parts) > 3  else 0.0
        ptn.r_v3 = _mv_to_v(parts[4])  if len(parts) > 4  else 0.0
        ptn.r_v4 = _mv_to_v(parts[5])  if len(parts) > 5  else 0.0

        # G V1~V4
        ptn.g_v1 = _mv_to_v(parts[6])  if len(parts) > 6  else 0.0
        ptn.g_v2 = _mv_to_v(parts[7])  if len(parts) > 7  else 0.0
        ptn.g_v3 = _mv_to_v(parts[8])  if len(parts) > 8  else 0.0
        ptn.g_v4 = _mv_to_v(parts[9])  if len(parts) > 9  else 0.0

        # B V1~V4
        ptn.b_v1 = _mv_to_v(parts[10]) if len(parts) > 10 else 0.0
        ptn.b_v2 = _mv_to_v(parts[11]) if len(parts) > 11 else 0.0
        ptn.b_v3 = _mv_to_v(parts[12]) if len(parts) > 12 else 0.0
        ptn.b_v4 = _mv_to_v(parts[13]) if len(parts) > 13 else 0.0

        # W V1~V4
        ptn.w_v1 = _mv_to_v(parts[14]) if len(parts) > 14 else 0.0
        ptn.w_v2 = _mv_to_v(parts[15]) if len(parts) > 15 else 0.0
        ptn.w_v3 = _mv_to_v(parts[16]) if len(parts) > 16 else 0.0
        ptn.w_v4 = _mv_to_v(parts[17]) if len(parts) > 17 else 0.0

        try:
            ptn.ptn_type = int(parts[18]) if len(parts) > 18 else 0
        except ValueError:
            ptn.ptn_type = 0

        return ptn


# ────────────────────────────────────────────────────────────────
# 편의 함수
# ────────────────────────────────────────────────────────────────

def otd_signal_to_signal_dict(otd_sig: OtdSignal) -> dict:
    """
    OtdSignal → Signal.from_dict() 에 사용 가능한 딕셔너리로 변환
    
    inversion / sig_mode 는 OTD의 MOD/INV 값에서 파생.
    """
    try:
        inv = int(otd_sig.inv)
    except ValueError:
        inv = 0
    try:
        mod = int(otd_sig.mod)
    except ValueError:
        mod = 0

    return {
        'name': otd_sig.name or otd_sig.num,
        'sig_type': str(otd_sig.sig_type),
        'sig_mode': mod,
        'inversion': inv,
        'v1': otd_sig.v1,
        'v2': otd_sig.v2,
        'v3': otd_sig.v3,
        'v4': otd_sig.v4,
        'delay': otd_sig.delay,
        'width': otd_sig.width,
        'period': otd_sig.period,
        'color': otd_sig.color,
        'visible': True,
        # 확장 필드
        'num': otd_sig.num,
        'length': otd_sig.length,
        'area': otd_sig.area,
    }


# ════════════════════════════════════════════════════════
# OtdFile → ModelStore 변환 헬퍼
# [통합] 구 otd_to_model_store.py에서 이동
# ════════════════════════════════════════════════════════

def otd_file_to_model_store(otd_file: OtdFile):
    """
    OtdFile 객체를 ModelStore 호환 데이터로 변환.

    OtdParser.parse()가 반환한 OtdFile을 받아
    ModelStore.set_models()에 바로 넣을 수 있는
    (List[ModelData], List[MultiRemoteGroup]) 튜플로 변환합니다.

    변환 흐름:
      OtdFile.models  → List[ModelData]
        OtdSignal     → Signal (otd_signal_to_signal_dict 경유)
        OtdPattern    → dict (패턴 파라미터 딕셔너리)
      OtdFile.multi_remotes → List[MultiRemoteGroup]
        MultiRemoteEntry    → MrtEntry

    신호 색상:
      matplotlib 기본 10색 팔레트를 순환 할당합니다.

    Args:
        otd_file (OtdFile): OtdParser.parse()로 파싱된 OTD 파일 객체

    Returns:
        tuple:
          - List[ModelData]        : 모든 모델 데이터
          - List[MultiRemoteGroup] : MULTIREMOTE 그룹(없으면 빈 리스트)
    """
    from model_store import ModelData, MultiRemoteGroup, MrtEntry
    from signal_model import Signal

    # matplotlib 기본 10색 팔레트 (신호 색상 순환 할당)
    default_colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    ]

    # ── OtdModel → ModelData 변환 ────────────────────────
    model_list = []
    for otd_model in otd_file.models:
        # OtdSignal → Signal (단위 변환 포함: mV→V, 1/10us→us)
        signals = []
        for i, otd_sig in enumerate(otd_model.signals):
            sig_dict = otd_signal_to_signal_dict(otd_sig)
            sig_dict['color'] = default_colors[i % len(default_colors)]
            signals.append(Signal.from_dict(sig_dict))

        # OtdPattern → 딕셔너리 (PatternDataPanel 호환 형식)
        patterns = [
            {
                'ptn_no': p.ptn_no,
                'name':   p.name,
                'r_v1': p.r_v1, 'r_v2': p.r_v2, 'r_v3': p.r_v3, 'r_v4': p.r_v4,
                'g_v1': p.g_v1, 'g_v2': p.g_v2, 'g_v3': p.g_v3, 'g_v4': p.g_v4,
                'b_v1': p.b_v1, 'b_v2': p.b_v2, 'b_v3': p.b_v3, 'b_v4': p.b_v4,
                'w_v1': p.w_v1, 'w_v2': p.w_v2, 'w_v3': p.w_v3, 'w_v4': p.w_v4,
                'ptn_type': p.ptn_type,
            }
            for p in otd_model.patterns
        ]

        model_list.append(ModelData(
            model_num    = otd_model.model_num,
            name         = otd_model.name,
            frequency_hz = otd_model.sync_freq_hz,
            sync_data_us = otd_model.sync_data_us,
            sync_cntr    = otd_model.sync_cntr,
            signals      = signals,
            patterns     = patterns,
        ))

    # ── MultiRemote → MultiRemoteGroup 변환 ──────────────
    mrt_groups = []
    for mr in otd_file.multi_remotes:
        entries = [
            MrtEntry(
                seq       = e.order,
                model_num = str(e.model_num),
                ptn_no    = e.pattern_num,
                time      = int(e.time),
            )
            for e in mr.entries
        ]
        mrt_groups.append(MultiRemoteGroup(
            mrt_no  = mr.mrt_id,
            name    = mr.name,
            entries = entries,
        ))

    return model_list, mrt_groups


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        result = OtdParser.parse(sys.argv[1])
        print(f"헤더: {result.header}")
        print(f"모델 수: {len(result.models)}")
        for m in result.models:
            print(f"  MODEL {m.model_num}: {m.name}, {m.sync_freq_hz:.2f}Hz, "
                  f"신호 {len(m.signals)}개, 패턴 {len(m.patterns)}개")
        print(f"MULTIREMOTE 수: {len(result.multi_remotes)}")
        for mr in result.multi_remotes:
            print(f"  MRT {mr.mrt_id}: {mr.name}, 항목 {len(mr.entries)}개")
