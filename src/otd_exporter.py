"""
OTD 파일 내보내기 모듈
프로그램 내 신호/패턴 데이터를 TOSG-400M OTD 파일 포맷으로 저장합니다.

OTD 포맷 규칙:
  - HEADER (1000번대): 장비 정보, 2줄 공백(\n\n)으로 구분
  - MODEL (100번대): 모델 정보
  - SIGNAL_DATA (200번대): 전압 mV, 시간 1/10us
  - PATTERN_DATA (400번대): 전압 mV
  - 999=END-MODEL_XXX: 모델 종료 (모델 간 3줄 공백)
  - GLOBAL_MRT / MULTIREMOTE (52= / 500~600번대)
  - 9999=END: 파일 종료
"""

from typing import List, Dict, Optional


# ────────────────────────────────────────────────────────────────
# 단위 변환 헬퍼
# ────────────────────────────────────────────────────────────────

def _v_to_mv(v: float) -> int:
    """V → mV (정수)"""
    return int(round(v * 1000))


def _us_to_tenth_us(us: float) -> int:
    """us → 1/10us (정수)"""
    return int(round(us * 10))


def _hz_to_sync_data_raw(hz: float) -> int:
    """주파수(Hz) → SYNCDATA 원본값 (1/10us 단위)
    
    SYNCDATA = 10,000,000 / Hz
    """
    if hz <= 0:
        return 0
    return int(round(10_000_000.0 / hz))


# ────────────────────────────────────────────────────────────────
# 포맷 파일(빈 템플릿) 생성
# ────────────────────────────────────────────────────────────────

DEFAULT_HEADER = {
    'device': 'LCD SHORTING BAR',
    'name': 'TOSG-400M',
    'pg_version': 'V5.0.9',
    'feature': 'CH36',
    'filesystem': 'V5.2.4',
    'compatibility': '3',
    'filetype': 'PG',
    'option1': '1',
    'option2': '0',
    'model_number': '1',
    'group_number': '1',
}

SIGNAL_TYPE_NAMES = {0: 'NONE', 1: 'CLK', 2: 'REF', 3: 'RED', 4: 'GREEN', 5: 'BLUE', 6: 'DATA'}
PATTERN_TYPE_NAMES = {
    0: '-', 1: 'A', 2: 'B', 3: 'PF1', 4: 'PF2', 5: 'PF3',
    6: 'ZIV', 7: 'ZRB', 8: 'ZRB2', 9: 'ZRB3', 10: 'MUX4D', 11: 'MUX1D'
}


class OtdExporter:
    """
    OTD 파일 생성기
    
    사용법:
        exporter = OtdExporter()
        exporter.export(filepath, models, header_overrides)
    """

    def export(
        self,
        filepath: str,
        models: List[Dict],
        header: Optional[Dict] = None,
        add_global_mrt: bool = False,
    ) -> bool:
        """
        OTD 파일 저장
        
        Args:
            filepath: 저장할 파일 경로
            models: 모델 데이터 리스트
                각 항목: {
                    'model_num': str,   # 예: '001'
                    'name': str,
                    'frequency_hz': float,
                    'sync_cntr': int,
                    'signals': List[dict],  # Signal.to_dict() 형식
                    'patterns': List[dict], # pattern dict
                }
            header: 헤더 오버라이드 딕셔너리 (DEFAULT_HEADER 기본값 사용)
            add_global_mrt: GLOBAL_MRT 섹션 추가 여부
            
        Returns:
            bool: 성공 여부
        """
        try:
            lines = []
            hdr = {**DEFAULT_HEADER, **(header or {})}

            # ── HEADER (1000번대) ───────────────────────────────
            lines.append(f"1001=DEVICE,{hdr['device']}")
            lines.append(f"1002=NAME,{hdr['name']}")
            lines.append(f"1003=PG_VERSION.{hdr['pg_version']}")
            lines.append(f"1004=FEATURE,{hdr['feature']}")
            lines.append(f"1005=FILESYSTEM,{hdr['filesystem']}")
            lines.append(f"1006=COMPATIBILITY,{hdr['compatibility']}")
            lines.append(f"1007=FILETYPE,{hdr['filetype']}")
            lines.append(f"1008=OPTION1,{hdr['option1']}")
            lines.append(f"1009=OPTION2,{hdr['option2']}")
            lines.append(f"1010=CURRENT.MODEL_NUMBER,{hdr['model_number']}")
            lines.append(f"1011=CURRENT_GROUP NUMBER,{hdr['group_number']}")
            lines.append("")   # 2줄 공백 (HEADER 뒤)
            lines.append("")

            # ── MODEL 블록들 ────────────────────────────────────
            for model_idx, model in enumerate(models):
                model_num = str(model.get('model_num', f'{model_idx+1:03d}'))
                model_name = model.get('name', f'Model-{model_num}')
                freq_hz = float(model.get('frequency_hz', 60.0))
                sync_cntr = int(model.get('sync_cntr', 0))
                signals = model.get('signals', [])
                patterns = model.get('patterns', [])

                sync_data_raw = _hz_to_sync_data_raw(freq_hz)

                # MODEL 헤더 (100번대)
                lines.append(f"101=MODEL,{model_num}")
                lines.append(f"102=NAME,{model_name}")
                lines.append(f"103=SYNCDATA,{sync_data_raw}")
                lines.append(f"104=SYNCCNTR,{sync_cntr}")
                lines.append("")

                # SIGNAL_DATA (200번대)
                for sig_idx, sig in enumerate(signals, start=1):
                    lines.append(self._format_signal_line(sig_idx, sig))

                lines.append("")

                # PATTERN_DATA (400번대)
                for ptn_idx, ptn in enumerate(patterns, start=1):
                    lines.append(self._format_pattern_line(ptn_idx, ptn))

                lines.append("")
                lines.append(f"999=END-MODEL_{model_num}")

                # 모델 간 3줄 공백
                if model_idx < len(models) - 1:
                    lines.append("")
                    lines.append("")
                    lines.append("")

            # ── GLOBAL_MRT ──────────────────────────────────────
            if add_global_mrt:
                lines.append("")
                lines.append("")

            # ── 파일 종료 ────────────────────────────────────────
            lines.append("")
            lines.append("9999=END")

            with open(filepath, 'w', encoding='utf-8', newline='\r\n') as f:
                f.write('\n'.join(lines))

            return True

        except Exception as e:
            print(f"OTD 내보내기 실패: {e}")
            return False

    def _format_signal_line(self, idx: int, sig: dict) -> str:
        """
        신호 데이터를 OTD 라인 포맷으로 변환
        
        포맷: 201-S01,NAME,V1,V2,V3,V4,DELAY,WIDTH,PERIOD,LENGTH,AREA,MF,MOD,INV,TYPE
        단위: 전압=mV, 시간=1/10us
        """
        num_str = sig.get('num', f'S{idx:02d}')
        name = sig.get('name', f'Signal{idx}')

        v1 = _v_to_mv(float(sig.get('v1', 0)))
        v2 = _v_to_mv(float(sig.get('v2', 0)))
        v3 = _v_to_mv(float(sig.get('v3', 0)))
        v4 = _v_to_mv(float(sig.get('v4', 0)))

        delay  = _us_to_tenth_us(float(sig.get('delay',  0)))
        width  = _us_to_tenth_us(float(sig.get('width',  0)))
        period = _us_to_tenth_us(float(sig.get('period', 0)))
        length = _us_to_tenth_us(float(sig.get('length', 0)))
        area   = _us_to_tenth_us(float(sig.get('area',   0)))

        mf  = sig.get('mf',  '0')
        mod = sig.get('sig_mode', 0)
        inv = sig.get('inversion', 0)

        sig_type_raw = sig.get('sig_type', '0')
        try:
            sig_type = int(sig_type_raw)
        except (ValueError, TypeError):
            sig_type = 0

        line_key = f"2{idx:02d}-{num_str}"
        return (f"{line_key},{name},{v1},{v2},{v3},{v4},"
                f"{delay},{width},{period},{length},{area},"
                f"{mf},{mod},{inv},{sig_type}")

    def _format_pattern_line(self, idx: int, ptn: dict) -> str:
        """
        패턴 데이터를 OTD 라인 포맷으로 변환
        
        포맷: 401=PTN01,NAME,R_V1,R_V2,R_V3,R_V4,G_V1~V4,B_V1~V4,W_V1~V4,TYPE
        단위: 전압=mV
        """
        ptn_num = ptn.get('ptn_no', idx)
        ptn_name = ptn.get('name', f'PTN{ptn_num:02d}')

        def mv(key): return _v_to_mv(float(ptn.get(key, 0)))

        r_v1, r_v2, r_v3, r_v4 = mv('r_v1'), mv('r_v2'), mv('r_v3'), mv('r_v4')
        g_v1, g_v2, g_v3, g_v4 = mv('g_v1'), mv('g_v2'), mv('g_v3'), mv('g_v4')
        b_v1, b_v2, b_v3, b_v4 = mv('b_v1'), mv('b_v2'), mv('b_v3'), mv('b_v4')
        w_v1, w_v2, w_v3, w_v4 = mv('w_v1'), mv('w_v2'), mv('w_v3'), mv('w_v4')
        ptn_type = ptn.get('ptn_type', 0)

        line_key = f"4{idx:02d}=PTN{ptn_num:02d}"
        return (f"{line_key},{ptn_name},"
                f"{r_v1},{r_v2},{r_v3},{r_v4},"
                f"{g_v1},{g_v2},{g_v3},{g_v4},"
                f"{b_v1},{b_v2},{b_v3},{b_v4},"
                f"{w_v1},{w_v2},{w_v3},{w_v4},"
                f"{ptn_type}")

    def export_format_file(self, filepath: str, model_count: int = 1) -> bool:
        """
        빈 OTD 포맷 파일(템플릿) 생성
        헤더와 빈 모델 구조만 포함된 템플릿을 저장합니다.
        
        Args:
            filepath: 저장할 파일 경로
            model_count: 생성할 빈 모델 수
        """
        empty_models = []
        for i in range(1, model_count + 1):
            empty_models.append({
                'model_num': f'{i:03d}',
                'name': f'Model-{i:03d}',
                'frequency_hz': 60.0,
                'sync_cntr': 0,
                'signals': [],
                'patterns': [],
            })
        return self.export(filepath, empty_models)


def otd_file_to_export_models(otd_file) -> List[Dict]:
    """
    OtdFile 객체를 OtdExporter.export()가 받는 models 리스트로 변환
    
    Args:
        otd_file: OtdFile 파싱 결과 객체
        
    Returns:
        List[Dict]: 내보내기 형식의 모델 딕셔너리 리스트
    """
    from otd_parser import otd_signal_to_signal_dict

    export_models = []
    for m in otd_file.models:
        signals = [otd_signal_to_signal_dict(s) for s in m.signals]
        patterns = [
            {
                'ptn_no': p.ptn_no,
                'name': p.name,
                'r_v1': p.r_v1, 'r_v2': p.r_v2, 'r_v3': p.r_v3, 'r_v4': p.r_v4,
                'g_v1': p.g_v1, 'g_v2': p.g_v2, 'g_v3': p.g_v3, 'g_v4': p.g_v4,
                'b_v1': p.b_v1, 'b_v2': p.b_v2, 'b_v3': p.b_v3, 'b_v4': p.b_v4,
                'w_v1': p.w_v1, 'w_v2': p.w_v2, 'w_v3': p.w_v3, 'w_v4': p.w_v4,
                'ptn_type': p.ptn_type,
            }
            for p in m.patterns
        ]
        export_models.append({
            'model_num': m.model_num,
            'name': m.name,
            'frequency_hz': m.sync_freq_hz,
            'sync_cntr': m.sync_cntr,
            'signals': signals,
            'patterns': patterns,
        })
    return export_models
