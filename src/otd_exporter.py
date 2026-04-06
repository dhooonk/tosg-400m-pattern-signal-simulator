"""
OTD 파일 내보내기 모듈

ModelStore의 전체 모델 데이터를 OTD 파일로 저장합니다.
MULTIREMOTE 섹션도 포함합니다.

OTD 포맷 구조 (수정된 형식):
  [HEADER]
  1001~1011번대

  [MODEL_XXX]
  101=MODEL,...
  102=NAME,...
  103=SYNCDATA,...
  104=SYNCCNTR,...
  [SIGNAL_DATA_XXX]       ← MODEL과 띄움 없이 바로
  201-S01=...
  ...
  [PATTERN_DATA_XXX]      ← SIGNAL_DATA와 띄움 없이 바로
  401=PTN01,...
  ...
  (마지막 PTN 바로 다음 줄)
  999=END-MODEL_XXX       ← 띄움 없이 바로
  (다음 모델이 있으면 4줄 띄움)

  [GLOBAL_MRT]            ← 마지막 모델과 바로 연결 없이
  52=FIRST_MRTGROUP,001
  [MULTIREMOTE_001]       ← GLOBAL_MRT와 띄움 없이 바로
  501=MRT,001,이름
  601=MRT01,...
  ...
  630=MRT30,...
  999=END
  [MULTIREMOTE_002]       ← 이전 999=END 바로 다음
  ...
  999=END
  9999=END                ← 마지막 999=END 바로 다음
"""

from typing import List, Dict, Optional


def _v_to_mv(v: float) -> int:
    """전압(V) → 밀리볼트(mV) 정수 변환"""
    return int(round(v * 1000))


def _us_to_tenth_us(us: float) -> int:
    """마이크로초(us) → 1/10us 정수 변환 (OTD 내부 단위)"""
    return int(round(us * 10))


def _hz_to_sync_data_raw(hz: float) -> int:
    """주파수(Hz) → SYNCDATA raw 값 변환 (단위: 1/10us)"""
    if hz <= 0:
        return 0
    return int(round(10_000_000.0 / hz))


# OTD 파일 헤더 기본값
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


class OtdExporter:
    """
    OTD 파일 생성기

    주요 메서드:
      - export_from_model_store(): ModelStore 인스턴스에서 직접 내보내기
      - export(): 딕셔너리 리스트 기반 내보내기 (범용)
    """

    def export_from_model_store(self, filepath: str, model_store,
                                 header: Optional[Dict] = None) -> bool:
        """
        ModelStore의 전체 데이터를 OTD 파일로 저장

        Args:
            filepath: 저장 경로
            model_store: ModelStore 인스턴스
            header: 헤더 오버라이드 딕셔너리 (None이면 기본값 사용)

        Returns:
            bool: 성공 여부
        """
        models_data = []
        for md in model_store.models:
            # Signal 객체면 to_dict()로 변환, 이미 dict면 그대로 사용
            signals = [s.to_dict() if hasattr(s, 'to_dict') else s
                       for s in md.signals]
            models_data.append({
                'model_num':    md.model_num,
                'name':         md.name,
                'frequency_hz': md.frequency_hz,
                'sync_data_us': md.sync_data_us,
                'sync_cntr':    md.sync_cntr,
                'signals':      signals,
                'patterns':     md.patterns,
            })
        return self.export(filepath, models_data,
                           header=header,
                           multiremote_groups=model_store.multiremote_groups)

    def export(self, filepath: str, models: List[Dict],
               header: Optional[Dict] = None,
               multiremote_groups=None) -> bool:
        """
        OTD 파일 저장

        각 섹션의 줄바꿈 규칙:
          - [MODEL_XXX]~[SIGNAL_DATA_XXX]: 줄바꿈 없음
          - [SIGNAL_DATA_XXX]~[PATTERN_DATA_XXX]: 줄바꿈 없음
          - 마지막 PTN~999=END-MODEL_XXX: 줄바꿈 없음
          - 999=END-MODEL_XXX~다음 [MODEL_XXX]: 4줄 공백
          - [GLOBAL_MRT]~[MULTIREMOTE_XXX]: 줄바꿈 없음
          - 각 MULTIREMOTE 끝에 999=END 추가
          - 마지막 999=END~9999=END: 줄바꿈 없음

        Args:
            filepath: 저장할 파일 경로
            models: 모델 데이터 딕셔너리 리스트
            header: 헤더 오버라이드 딕셔너리
            multiremote_groups: List[MultiRemoteGroup]

        Returns:
            bool: 성공이면 True, 실패이면 False
        """
        try:
            lines = []
            hdr = {**DEFAULT_HEADER, **(header or {})}

            # ── [HEADER] 섹션 ────────────────────────────────────
            hdr_num = str(len(models)) if models else '1'
            lines += [
                '[HEADER]',
                f"1001=DEVICE,{hdr['device']}",
                f"1002=NAME,{hdr['name']}",
                f"1003=PG_VERSION,{hdr['pg_version']}",
                f"1004=FEATURE,{hdr['feature']}",
                f"1005=FILESYSTEM,{hdr['filesystem']}",
                f"1006=COMPATIBILITY,{hdr['compatibility']}",
                f"1007=FILETYPE,{hdr['filetype']}",
                f"1008=OPTION1,{hdr['option1']}",
                f"1009=OPTION2,{hdr['option2']}",
                f"1010=CURRENT_MODEL_NUMBER,{hdr_num}",
                f"1011=CURRENT_GROUP NUMBER,{hdr['group_number']}",
                "", "",
            ]

            # ── MODEL 블록들 ──────────────────────────────────────
            for model_idx, model in enumerate(models):
                model_num    = str(model.get('model_num', f'{model_idx+1:03d}'))
                model_name   = model.get('name', f'Model-{model_num}')
                freq_hz      = float(model.get('frequency_hz', 60.0))
                sync_data_us = float(model.get('sync_data_us', 0))
                sync_cntr    = int(model.get('sync_cntr', 0))
                signals      = model.get('signals', [])
                patterns     = model.get('patterns', [])

                # SYNCDATA raw 계산
                if sync_data_us > 0:
                    sync_raw = _us_to_tenth_us(sync_data_us)
                else:
                    sync_raw = _hz_to_sync_data_raw(freq_hz)

                # [MODEL_XXX] 섹션
                lines += [
                    f'[MODEL_{model_num}]',
                    f"101=MODEL,{model_num}",
                    f"102=NAME,{model_name}",
                    f"103=SYNCDATA,{sync_raw}",
                    f"104=SYNCCNTR,{sync_cntr}",
                ]

                # [SIGNAL_DATA_XXX]: 바로 이어서 (빈줄 없음)
                lines.append(f'[SIGNAL_DATA_{model_num}]')
                for sig_idx, sig in enumerate(signals, 1):
                    lines.append(self._format_signal_line(sig_idx, sig))

                # [PATTERN_DATA_XXX]: 바로 이어서 (빈줄 없음)
                lines.append(f'[PATTERN_DATA_{model_num}]')
                for ptn_idx, ptn in enumerate(patterns, 1):
                    lines.append(self._format_pattern_line(ptn_idx, ptn))

                # 999=END-MODEL_XXX: 마지막 PTN 바로 다음 (빈줄 없음)
                lines.append(f"999=END-MODEL_{model_num}")

                # 다음 모델과의 간격: 4줄 공백
                if model_idx < len(models) - 1:
                    lines += ["", "", "", ""]

            # ── GLOBAL_MRT 섹션 ──────────────────────────────────
            if multiremote_groups:
                # GLOBAL_MRT는 마지막 모델 끝 다음에 빈줄 없이 바로 (피드백 6번)
                lines += ["", ""]
                lines.append('[GLOBAL_MRT]')
                # 52=FIRST_MRTGROUP,001 형식 (피드백 5번)
                for grp in multiremote_groups:
                    lines.append(f"52=FIRST_MRTGROUP,{grp.mrt_no}")

                # [MULTIREMOTE_XXX]: GLOBAL_MRT 바로 다음 (빈줄 없음)
                for grp in multiremote_groups:
                    lines.append(f'[MULTIREMOTE_{grp.mrt_no}]')
                    # 501=MRT,번호,이름 형식 (피드백 7번)
                    lines.append(f"501=MRT,{grp.mrt_no},{grp.name}")
                    for entry in grp.entries:
                        lines.append(
                            f"6{entry.seq:02d}=MRT{entry.seq:02d},"
                            f"{entry.model_num},{entry.ptn_no},{entry.time}"
                        )
                    # 각 MULTIREMOTE 블록 끝에 999=END 추가 (피드백 8번)
                    lines.append("999=END")
                    # 다음 MULTIREMOTE 블록은 바로 이어서 (빈줄 없음, 피드백 9번)

                # 9999=END: 마지막 999=END 바로 다음 (빈줄 없음, 피드백 10번)
                lines.append("9999=END")
            else:
                # MULTIREMOTE가 없는 경우
                lines += ["", "9999=END"]

            with open(filepath, 'w', encoding='utf-8', newline='\r\n') as f:
                f.write('\n'.join(lines))
            return True

        except Exception as e:
            print(f"OTD 내보내기 실패: {e}")
            import traceback; traceback.print_exc()
            return False

    def _format_signal_line(self, idx: int, sig: dict) -> str:
        """
        신호 딕셔너리를 OTD SIGNAL_DATA 라인 형식으로 변환

        OTD 포맷: 2XX-SYY=NUM,NAME,V1,V2,V3,V4,DELAY,WIDTH,PERIOD,LENGTH,AREA,MF,MOD,INV,TYPE
        단위 변환: 전압 V→mV, 시간 us→1/10us
        """
        num_str = sig.get('num', f'S{idx:02d}')
        name    = sig.get('name', f'Signal{idx}')
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
        try:
            sig_type = int(sig.get('sig_type', '0'))
        except (ValueError, TypeError):
            sig_type = 0
        line_key = f"2{idx:02d}-{num_str}"
        return (f"{line_key}={name},{v1},{v2},{v3},{v4},"
                f"{delay},{width},{period},{length},{area},"
                f"{mf},{mod},{inv},{sig_type}")

    def _format_pattern_line(self, idx: int, ptn: dict) -> str:
        """
        패턴 딕셔너리를 OTD PATTERN_DATA 라인 형식으로 변환

        OTD 포맷: 4XX=PTNXX,NAME,R_V1..V4,G_V1..V4,B_V1..V4,W_V1..V4,TYPE
        단위 변환: 전압 V→mV
        """
        ptn_num  = ptn.get('ptn_no', idx)
        ptn_name = ptn.get('name', f'PTN{ptn_num:02d}')

        def mv(k):
            return _v_to_mv(float(ptn.get(k, 0)))

        r1, r2, r3, r4 = mv('r_v1'), mv('r_v2'), mv('r_v3'), mv('r_v4')
        g1, g2, g3, g4 = mv('g_v1'), mv('g_v2'), mv('g_v3'), mv('g_v4')
        b1, b2, b3, b4 = mv('b_v1'), mv('b_v2'), mv('b_v3'), mv('b_v4')
        w1, w2, w3, w4 = mv('w_v1'), mv('w_v2'), mv('w_v3'), mv('w_v4')
        ptn_type = ptn.get('ptn_type', 0)
        line_key = f"4{idx:02d}=PTN{ptn_num:02d}"
        return (f"{line_key},{ptn_name},"
                f"{r1},{r2},{r3},{r4},{g1},{g2},{g3},{g4},"
                f"{b1},{b2},{b3},{b4},{w1},{w2},{w3},{w4},{ptn_type}")
