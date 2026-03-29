def otd_file_to_model_store(otd_file):
    """
    OtdFile → ModelStore 에 설정할 데이터로 변환

    Returns:
        (List[ModelData], List[MultiRemoteGroup])
    """
    from model_store import ModelData, MultiRemoteGroup, MrtEntry
    from signal_model import Signal

    default_colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    ]

    model_list = []
    for otd_model in otd_file.models:
        signals = []
        for i, otd_sig in enumerate(otd_model.signals):
            sig_dict = otd_signal_to_signal_dict(otd_sig)
            sig_dict['color'] = default_colors[i % len(default_colors)]
            signals.append(Signal.from_dict(sig_dict))

        patterns = [
            {
                'ptn_no': p.ptn_no, 'name': p.name,
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

    # MULTIREMOTE 변환
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
