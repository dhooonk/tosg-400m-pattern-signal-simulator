"""
OTD → ModelStore 변환 모듈

OtdParser.parse()로 파싱된 OtdFile 객체를 ModelStore에서 사용하는
ModelData 리스트와 MultiRemoteGroup 리스트로 변환합니다.

사용 흐름:
  1. OtdParser.parse(filepath) → OtdFile
  2. otd_file_to_model_store(otd_file) → (List[ModelData], List[MultiRemoteGroup])
  3. model_store.set_models(model_list, mrt_groups)
"""

from otd_parser import OtdSignal, otd_signal_to_signal_dict


def otd_file_to_model_store(otd_file):
    """
    OtdFile 객체를 ModelStore 호환 데이터로 변환

    OtdFile에 포함된 모든 모델과 MULTIREMOTE 데이터를 변환합니다.

    Args:
        otd_file (OtdFile): OtdParser.parse()로 파싱된 OTD 파일 객체

    Returns:
        tuple:
            - List[ModelData]: 모든 모델 데이터 리스트
            - List[MultiRemoteGroup]: MULTIREMOTE 그룹 리스트
    """
    from model_store import ModelData, MultiRemoteGroup, MrtEntry
    from signal_model import Signal

    # 신호 색상 팔레트 (matplotlib 기본 10색)
    default_colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    ]

    # ── OtdModel → ModelData 변환 ──────────────────────────────
    model_list = []
    for otd_model in otd_file.models:
        # OtdSignal → Signal 변환
        signals = []
        for i, otd_sig in enumerate(otd_model.signals):
            sig_dict = otd_signal_to_signal_dict(otd_sig)
            # 색상 팔레트에서 순환 할당
            sig_dict['color'] = default_colors[i % len(default_colors)]
            signals.append(Signal.from_dict(sig_dict))

        # OtdPattern → 딕셔너리 변환 (PatternDataPanel 호환)
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

    # ── MultiRemote → MultiRemoteGroup 변환 ───────────────────
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
