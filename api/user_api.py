from models.user import User
from models.candidate import Candidate
from models.search_params import SearchParams

from typing import Optional, List, Dict, Any
from api.client import VKClient


class VKUserAPI:
    """Обёртка над методами VK API для работы с пользователями"""
    
    def __init__(self, client: VKClient):
        self.client = client
    
    def get_user_info(self, user_id: int, fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о пользователе ВКонтакте
        
        :param user_id: ID пользователя
        :param fields: Список дополнительных полей для получения
        :return: Словарь с данными пользователя или None при ошибке
        """
        # Поля, которые нам нужны для логики подбора
        if fields is None:
            fields = [
                'sex', 'bdate', 'city', 'relation', 'photo_200', 
                'photo_max_orig', 'verified', 'can_access_closed', 'is_closed'
            ]
        
        params = {
            'user_ids': user_id,
            'fields': ','.join(fields),
            'v': '5.131'  # Версия API (фиксируем, чтобы не ломалось при обновлениях)
        }
        
        try:
            response = self.client.call_method('users.get', params)
            if response and 'response' in response and len(response['response']) > 0:
                return response['response'][0]
        except Exception as e:
            print(f"❌ Ошибка при получении информации о пользователе {user_id}: {e}")
        
        return None
    
    def search_candidates(
        self,
        sex: int,
        age_from: int,
        age_to: int,
        city_id: int,
        offset: int = 0,
        count: int = 10,
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Ищет кандидатов для знакомств по заданным критериям
        
        :param sex: Пол (1 — женский, 2 — мужской)
        :param age_from: Минимальный возраст
        :param age_to: Максимальный возраст
        :param city_id: ID города
        :param offset: Смещение для пагинации
        :param count: Количество результатов
        :param fields: Дополнительные поля для получения
        :return: Список словарей с данными кандидатов
        """
        if fields is None:
            fields = [
                'id', 'first_name', 'last_name', 'sex', 'bdate', 
                'city', 'photo_200', 'photo_max_orig', 'verified',
                'can_access_closed', 'is_closed', 'relation'
            ]
        
        params = {
            'sex': sex,
            'age_from': age_from,
            'age_to': age_to,
            'city': city_id,
            'has_photo': 1,  # Только пользователи с аватаркой
            'fields': ','.join(fields),
            'offset': offset,
            'count': count,
            'v': '5.131'
        }
        
        try:
            response = self.client.call_method('users.search', params)
            if response and 'response' in response:
                # users.search возвращает {'count': N, 'items': [...]}
                return response['response'].get('items', [])
        except Exception as e:
            print(f"❌ Ошибка при поиске кандидатов: {e}")
        
        return []

    
    def search_candidates(self, search_params: SearchParams) -> list[Candidate]:
        # Здесь должна быть реализация поиска кандидатов в VK API на основе переданных параметров
        pass
