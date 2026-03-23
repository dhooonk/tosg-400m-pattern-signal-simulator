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
  - 999=END: 모델 종료
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
    """

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
            ValueError: 파일 형식이 올바르지 않을 때
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

            # ── 전체/모델 종료 ──────────────────────────────────
            if line == '9999=END':
                break
            if line.startswith('999=END'):
                # 모델 종료
                if current_model is not None:
                    result.models.append(current_model)
                    current_model = None
                if in_global_mrt:
                    # GLOBAL_MRT 블록 내 END
                    in_global_mrt = False
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
                # 숫자가 아닌 키 (예: 52)는 별도 처리
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
                current_model.model_num = value.split(',')[0] if ',' in value else value
                # 앞에 'MODEL,' 접두사 제거
                parts = value.split(',')
                current_model.model_num = parts[-1].strip() if parts else value
                continue

            if current_model is None:
                # GLOBAL_MRT / MULTIREMOTE 영역
                if 500 <= key_num < 600:
                    # MULTIREMOTE 헤더
                    current_mrt = MultiRemote()
                    parts = value.split(',', 1)
                    if len(parts) >= 1:
                        current_mrt.mrt_id = parts[0].strip()
                    if len(parts) >= 2:
                        current_mrt.name = parts[1].strip()
                    result.multi_remotes.append(current_mrt)
                elif 600 <= key_num < 700 and current_mrt is not None:
                    # MULTIREMOTE 실행 항목
                    parts = [p.strip() for p in value.split(',')]
                    entry = MultiRemoteEntry()
                    try:
                        entry.order = key_num - 600
                        entry.model_num = int(parts[0]) if len(parts) > 0 else 0
                        entry.pattern_num = int(parts[1]) if len(parts) > 1 else 0
                        entry.time = float(parts[2]) if len(parts) > 2 else 0.0
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
                        # 주파수 = 10,000,000 / sync_data_raw (단위: 1/10us → Hz)
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
        # value에 ',' 접두사(키 이름)가 있을 수 있음: "DEVICE,LCD SHORTING BAR"
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
        
        포맷: 201-S01,GND,0,0,0,0,0,0,0,0,0,0,0,0
        컬럼: NUM, NAME, V1, V2, V3, V4, DELAY, WIDTH, PERIOD, LENGTH, AREA, MF, MOD, INV, [TYPE]
        단위: 전압=mV, 시간=1/10us
        """
        # key에 '-'가 포함된 경우 (201-S01): value에 NUM이 포함되어 있음
        parts = [p.strip() for p in value.split(',')]
        if len(parts) < 2:
            return None

        sig = OtdSignal()
        sig.num = parts[0]  # S01
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
        
        포맷: 401=PTN01,VGL-10,-10000,18000,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
        컬럼: No., NAME, R_V1,R_V2,R_V3,R_V4, G_V1~V4, B_V1~V4, W_V1~V4, TYPE
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


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        result = OtdParser.parse(sys.argv[1])
        print(f"헤더: {result.header}")
        print(f"모델 수: {len(result.models)}")
        for m in result.models:
            print(f"  MODEL {m.model_num}: {m.name}, {m.sync_freq_hz:.2f}Hz, "
                  f"신호 {len(m.signals)}개, 패턴 {len(m.patterns)}개")
