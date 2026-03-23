"""
신호 저장/로드 모듈
모델별로 신호 데이터를 JSON 파일로 저장하고 불러오는 기능을 제공합니다.
"""

import json
import os


class SignalStorage:
    """
    신호 데이터 저장/로드 클래스
    
    신호 데이터를 JSON 형식으로 직렬화하여 파일 시스템에 저장하거나,
    저장된 파일에서 데이터를 읽어와 복원합니다.
    데이터는 'signal_data' 디렉토리 내에 모델 이름별로 저장됩니다.
    """
    
    def __init__(self, storage_dir='signal_data'):
        """
        초기화 메서드
        
        Args:
            storage_dir (str): 데이터 저장 디렉토리 경로 (기본값: 'signal_data')
        """
        self.storage_dir = storage_dir
        # 저장 디렉토리가 없으면 생성
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
    
    def get_file_path(self, model_name):
        """
        모델별 파일 경로 생성
        
        모델 이름을 기반으로 안전한 파일명을 생성합니다.
        
        Args:
            model_name (str): 모델 이름
            
        Returns:
            str: 전체 파일 경로
        """
        # 파일명에 사용할 수 없는 문자 제거 (알파벳, 숫자, -, _ 만 허용)
        safe_name = "".join(c for c in model_name if c.isalnum() or c in ('-', '_'))
        return os.path.join(self.storage_dir, f"{safe_name}.json")
    
    def save_signals(self, model_name, signals):
        """
        모델별 신호 저장
        
        주어진 모델 이름으로 신호 리스트를 JSON 파일에 저장합니다.
        
        Args:
            model_name (str): 모델 이름
            signals (list): 저장할 Signal 객체 리스트
        
        Returns:
            bool: 저장 성공 여부
        """
        try:
            file_path = self.get_file_path(model_name)
            
            # 저장할 데이터 구조 생성
            data = {
                'model': model_name,
                'signals': [signal.to_dict() for signal in signals]
            }
            
            # JSON 파일로 저장 (UTF-8 인코딩 사용)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"신호 저장 실패: {e}")
            return False
    
    def load_signals(self, model_name):
        """
        모델별 신호 로드
        
        주어진 모델 이름에 해당하는 JSON 파일에서 신호 데이터를 불러옵니다.
        
        Args:
            model_name (str): 모델 이름
        
        Returns:
            list: 로드된 Signal 객체 리스트 (파일이 없거나 실패 시 빈 리스트 반환)
        """
        try:
            file_path = self.get_file_path(model_name)
            
            if not os.path.exists(file_path):
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 딕셔너리 데이터를 Signal 객체로 변환
            from signal_model import Signal
            signals = [Signal.from_dict(sig_data) for sig_data in data.get('signals', [])]
            
            return signals
        except Exception as e:
            print(f"신호 로드 실패: {e}")
            return []
    
    def get_saved_models(self):
        """
        저장된 모델 목록 반환
        
        저장 디렉토리 내의 모든 JSON 파일을 검색하여 저장된 모델 목록을 반환합니다.
        
        Returns:
            list: 저장된 모델 이름 리스트
        """
        models = []
        try:
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.storage_dir, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        models.append(data.get('model', filename[:-5]))
        except Exception as e:
            print(f"모델 목록 조회 실패: {e}")
        
        return models
    
    def delete_model_data(self, model_name):
        """
        모델 데이터 삭제
        
        특정 모델의 저장된 데이터 파일을 삭제합니다.
        
        Args:
            model_name (str): 삭제할 모델 이름
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            file_path = self.get_file_path(model_name)
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception as e:
            print(f"모델 데이터 삭제 실패: {e}")
        
        return False
    
    def save_signals_to_file(self, filepath, signals):
        """
        사용자 지정 파일 경로로 신호 저장
        
        Args:
            filepath (str): 저장할 파일 경로 (전체 경로)
            signals (list): 저장할 Signal 객체 리스트
        
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 저장할 데이터 구조 생성
            data = {
                'signals': [signal.to_dict() for signal in signals]
            }
            
            # JSON 파일로 저장 (UTF-8 인코딩 사용)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"신호 저장 실패: {e}")
            return False
    
    def load_signals_from_file(self, filepath):
        """
        사용자 지정 파일 경로에서 신호 로드
        
        Args:
            filepath (str): 불러올 파일 경로 (전체 경로)
        
        Returns:
            list: 로드된 Signal 객체 리스트 (파일이 없거나 실패 시 빈 리스트 반환)
        """
        try:
            if not os.path.exists(filepath):
                return []
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 딕셔너리 데이터를 Signal 객체로 변환
            from signal_model import Signal
            signals = [Signal.from_dict(sig_data) for sig_data in data.get('signals', [])]
            
            return signals
        except Exception as e:
            print(f"신호 로드 실패: {e}")
            return []
