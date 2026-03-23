"""
SyncData 관리 모듈
모델별 주파수 및 SyncData 계산 (SyncData = 1 / 주파수)을 담당합니다.
"""

import json
import os


class SyncDataManager:
    """
    모델 및 주파수별 SyncData 관리 클래스
    
    디스플레이 모델(크기)과 각 모델에서 지원하는 주파수 목록을 관리합니다.
    설정 파일(models_config.json)을 통해 모델 정보를 영구 저장하고 불러옵니다.
    
    Attributes:
        config_file (str): 설정 파일 경로
        models (dict): 모델 및 주파수 데이터 딕셔너리
        current_model (str): 현재 선택된 모델 이름
        current_frequency (int): 현재 선택된 주파수 (Hz)
    """
    
    # 기본 디스플레이 모델 및 주파수 데이터
    # 모델은 디스플레이 크기를 나타냅니다 (예: 12.3", 8.0", 38.9")
    # V8 업데이트: H Total, V Total 추가
    DEFAULT_MODELS = {
        '12.3"': {'frequencies': [60, 120, 240], 'h_total': 3000, 'v_total': 1000},
        '8.0"': {'frequencies': [60, 120], 'h_total': 2000, 'v_total': 800},
        '38.9"': {'frequencies': [60, 120, 240, 400], 'h_total': 4000, 'v_total': 2000},
    }
    
    def __init__(self, config_file='models_config.json'):
        """
        초기화 메서드
        
        Args:
            config_file (str): 설정 파일 이름 (기본값: 'models_config.json')
        """
        self.config_file = config_file
        self.models = {}
        self.current_model = None
        self.current_frequency = None
        self.load_models()
    
    def load_models(self):
        """
        모델 설정 파일 로드
        
        설정 파일이 존재하면 파일에서 데이터를 읽어오고,
        없거나 오류 발생 시 기본값(DEFAULT_MODELS)을 사용합니다.
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 구 버전 호환성 체크 (리스트 형태인 경우 딕셔너리로 변환)
                    self.models = {}
                    for k, v in data.items():
                        if isinstance(v, list):
                            self.models[k] = {'frequencies': v, 'h_total': 1000, 'v_total': 1000}
                        else:
                            self.models[k] = v
            except Exception as e:
                print(f"모델 설정 로드 실패: {e}")
                self.models = self.DEFAULT_MODELS.copy()
        else:
            self.models = self.DEFAULT_MODELS.copy()
            self.save_models()
        
        # 기본 모델 및 주파수 설정 (첫 번째 항목으로 초기화)
        if self.models:
            self.current_model = list(self.models.keys())[0]
            if self.models[self.current_model]['frequencies']:
                self.current_frequency = self.models[self.current_model]['frequencies'][0]
    
    def save_models(self):
        """
        모델 설정 파일 저장
        
        현재 모델 및 주파수 데이터를 JSON 파일로 저장합니다.
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.models, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"모델 설정 저장 실패: {e}")
    
    def get_model_list(self):
        """
        모델 목록 반환
        
        Returns:
            list: 사용 가능한 모든 모델 이름 리스트
        """
        return list(self.models.keys())
    
    def get_frequency_list(self, model=None):
        """
        특정 모델의 주파수 목록 반환
        
        Args:
            model (str, optional): 모델 이름. None이면 현재 모델 사용.
            
        Returns:
            list: 해당 모델의 지원 주파수 리스트 (Hz)
        """
        if model is None:
            model = self.current_model
        
        model_data = self.models.get(model)
        if model_data:
            return model_data.get('frequencies', [])
        return []
    
    def get_model_params(self, model=None):
        """
        모델의 파라미터(H Total, V Total) 반환
        
        Args:
            model (str, optional): 모델 이름. None이면 현재 모델 사용.
            
        Returns:
            dict: {'h_total': int, 'v_total': int}
        """
        if model is None:
            model = self.current_model
            
        model_data = self.models.get(model)
        if model_data:
            return {
                'h_total': model_data.get('h_total', 1000),
                'v_total': model_data.get('v_total', 1000)
            }
        return {'h_total': 1000, 'v_total': 1000}

    def set_model(self, model):
        """
        현재 모델 설정
        
        Args:
            model (str): 설정할 모델 이름
            
        Returns:
            bool: 설정 성공 여부
        """
        if model in self.models:
            self.current_model = model
            # 모델 변경 시 첫 번째 주파수로 자동 설정
            frequencies = self.models[model]['frequencies']
            if frequencies:
                self.current_frequency = frequencies[0]
            return True
        return False
    
    def set_frequency(self, frequency):
        """
        현재 주파수 설정
        
        Args:
            frequency (int): 설정할 주파수 (Hz)
            
        Returns:
            bool: 설정 성공 여부
        """
        if self.current_model and frequency in self.models[self.current_model]['frequencies']:
            self.current_frequency = frequency
            return True
        return False
    
    def get_sync_data(self, model=None, frequency=None):
        """
        SyncData 계산 (1 / 주파수)
        
        Args:
            model: 모델 이름 (None이면 현재 모델)
            frequency: 주파수 (None이면 현재 주파수)
        
        Returns:
            float: SyncData 값 (초 단위)
        """
        if model is None:
            model = self.current_model
        if frequency is None:
            frequency = self.current_frequency
        
        if frequency and frequency > 0:
            return 1.0 / frequency
        return 0.0
    
    def get_current_sync_data(self):
        """
        현재 설정의 SyncData 반환
        
        Returns:
            float: 현재 모델 및 주파수에 따른 SyncData 값 (초 단위)
        """
        return self.get_sync_data()
    
    def add_model(self, model_name, frequencies, h_total=1000, v_total=1000):
        """
        새 모델 추가
        
        Args:
            model_name (str): 추가할 모델 이름
            frequencies (list): 해당 모델의 주파수 리스트
            h_total (int): H Total 값
            v_total (int): V Total 값
        """
        self.models[model_name] = {
            'frequencies': frequencies,
            'h_total': h_total,
            'v_total': v_total
        }
        self.save_models()
    
    def remove_model(self, model_name):
        """
        모델 삭제
        
        Args:
            model_name (str): 삭제할 모델 이름
        """
        if model_name in self.models:
            del self.models[model_name]
            self.save_models()
            # 현재 모델이 삭제된 경우 다른 모델로 변경
            if self.current_model == model_name:
                if self.models:
                    self.set_model(list(self.models.keys())[0])
                else:
                    self.current_model = None
                    self.current_frequency = None
    
    def add_frequency(self, model_name, frequency):
        """
        모델에 주파수 추가
        
        Args:
            model_name (str): 대상 모델 이름
            frequency (int): 추가할 주파수 (Hz)
        """
        if model_name in self.models:
            freq_list = self.models[model_name]['frequencies']
            if frequency not in freq_list:
                freq_list.append(frequency)
                freq_list.sort()
                self.save_models()
    
    def remove_frequency(self, model_name, frequency):
        """
        모델에서 주파수 삭제
        
        Args:
            model_name (str): 대상 모델 이름
            frequency (int): 삭제할 주파수 (Hz)
        """
        if model_name in self.models:
            freq_list = self.models[model_name]['frequencies']
            if frequency in freq_list:
                freq_list.remove(frequency)
                self.save_models()
                # 현재 주파수가 삭제된 경우 다른 주파수로 변경
                if self.current_model == model_name and self.current_frequency == frequency:
                    if freq_list:
                        self.current_frequency = freq_list[0]
                    else:
                        self.current_frequency = None

    def _update_from_otd(self, model_id: str, model_name: str,
                         frequency_hz: int, sync_data_us: float):
        """
        OTD 파일에서 읽어온 모델/주파수 정보로 현재 상태 업데이트
        
        기존 모델 목록에 없는 경우 임시로 추가합니다(저장하지 않음).
        
        Args:
            model_id: 모델 번호 문자열 (예: '010')
            model_name: 모델 이름 (예: 'B5-BLUE-V')
            frequency_hz: 주파수 (Hz), 0이면 sync_data_us로 계산
            sync_data_us: 1프레임 길이 (us), 직접 저장용
        """
        # 표시 이름: "MODEL010: B5-BLUE-V" 형태
        display_name = f"OTD-{model_id}"
        if model_name:
            display_name = f"{model_name} [{model_id}]"

        # 주파수 보정
        if frequency_hz <= 0 and sync_data_us > 0:
            frequency_hz = int(round(1_000_000.0 / sync_data_us))
        if frequency_hz <= 0:
            frequency_hz = 60

        # 임시 모델 등록 (기존에 없으면)
        if display_name not in self.models:
            self.models[display_name] = {
                'frequencies': [frequency_hz],
                'h_total': 1000,
                'v_total': 1000,
                'sync_data_us': sync_data_us,
            }
        else:
            freq_list = self.models[display_name]['frequencies']
            if frequency_hz not in freq_list:
                freq_list.append(frequency_hz)
                freq_list.sort()
            self.models[display_name]['sync_data_us'] = sync_data_us

        self.current_model = display_name
        self.current_frequency = frequency_hz

    def get_current_sync_data_us(self) -> float:
        """
        현재 모델의 sync_data_us 반환 (us 단위)
        OTD에서 직접 읽어온 값이 있으면 그 값 사용, 없으면 1/주파수 계산.
        """
        if self.current_model and self.current_model in self.models:
            model_data = self.models[self.current_model]
            sync_us = model_data.get('sync_data_us', None)
            if sync_us is not None and sync_us > 0:
                return sync_us
        # fallback: 주파수로 계산
        sync_s = self.get_current_sync_data()
        return sync_s * 1_000_000

