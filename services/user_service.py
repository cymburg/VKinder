from models.user import User
from repositories.user_repository import UserRepository
from api.user_api import VKUserAPI

from datetime import datetime
from typing import List, Dict, Optional, Any
from api.user_api import VKUserAPI
from repositories.user_repository import UserRepository


class UserService:
    """Бизнес-логика работы с пользователями и кандидатами"""
    
    def __init__(self, user_api: VKUserAPI, user_repo: UserRepository):
        self.user_api = user_api
        self.user_repo = user_repo
    
    def _parse_age(self, bdate: Optional[str]) -> Optional[int]:
        """
        Извлекает возраст из даты рождения формата VK (DD.MM.YYYY или DD.MM)
        
        :param bdate: Строка даты от VK API
        :return: Возраст в годах или None, если год скрыт
        """
        if not bdate:
            return None
        
        parts = bdate.split('.')
        if len(parts) == 3:  # Есть год: '15.05.1995'
            try:
                birth_year = int(parts[2])
                current_year = datetime.now().year
                age = current_year - birth_year
                
                # Уточняем: если день рождения ещё не наступил в этом году
                birth_month, birth_day = int(parts[1]), int(parts[0])
                current_month, current_day = datetime.now().month, datetime.now().day
                if (current_month, current_day) < (birth_month, birth_day):
                    age -= 1
                return max(0, age)
            except (ValueError, IndexError):
                return None
        return None  # Год скрыт: '15.05'
    
    def get_current_user_profile(self, vk_user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает и обрабатывает профиль текущего пользователя
        
        :param vk_user_id: ID пользователя ВКонтакте
        :return: Словарь с подготовленными данными или None
        """
        raw_info = self.user_api.get_user_info(vk_user_id)
        if not raw_info:
            return None
        
        # Извлекаем город (city — это словарь {'id': ..., 'title': ...})
        city = raw_info.get('city')
        city_id = city['id'] if isinstance(city, dict) else None
        city_name = city.get('title') if isinstance(city, dict) else None
        
        return {
            'vk_id': raw_info.get('id'),
            'first_name': raw_info.get('first_name'),
            'last_name': raw_info.get('last_name'),
            'sex': raw_info.get('sex'),  # 1 = жен, 2 = муж
            'age': self._parse_age(raw_info.get('bdate')),
            'city_id': city_id,
            'city_name': city_name,
            'photo': raw_info.get('photo_200'),
            'is_closed': raw_info.get('is_closed', False)
        }
    
    def find_candidates(
        self,
        current_user_id: int,
        offset: int = 0,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Ищет кандидатов для знакомств с учётом фильтрации по БД
        
        :param current_user_id: ID текущего пользователя ВКонтакте
        :param offset: Смещение для пагинации
        :param count: Максимальное количество кандидатов
        :return: Список подготовленных кандидатов
        """
        # 1. Получаем профиль текущего пользователя
        profile = self.get_current_user_profile(current_user_id)
        if not profile or not profile['age'] or not profile['city_id']:
            return []
        
        # 2. Определяем критерии поиска (противоположный пол)
        target_sex = 2 if profile['sex'] == 1 else 1  # 1↔2
        age_from = max(14, profile['age'] - 3)  # Минимум 14 лет по правилам ВК
        age_to = profile['age'] + 3
        
        # 3. Получаем ID уже просмотренных и в чёрном списке
        excluded_ids = self.user_repo.get_excluded_user_ids(current_user_id)
        
        # 4. Ищем кандидатов через API (с запасом, т.к. часть отфильтруется)
        api_count = count + len(excluded_ids) + 5
        raw_candidates = self.user_api.search_candidates(
            sex=target_sex,
            age_from=age_from,
            age_to=age_to,
            city_id=profile['city_id'],
            offset=offset,
            count=api_count
        )
        
        # 5. Фильтруем и форматируем результаты
        candidates = []
        for candidate in raw_candidates:
            vk_id = candidate.get('id')
            
            # Пропускаем, если уже просмотрен/в ЧС
            if vk_id in excluded_ids:
                continue
            
            # Пропускаем закрытые профили (не сможем получить фото)
            if candidate.get('is_closed'):
                continue
            
            age = self._parse_age(candidate.get('bdate'))
            city = candidate.get('city')
            
            candidates.append({
                'vk_id': vk_id,
                'first_name': candidate.get('first_name'),
                'last_name': candidate.get('last_name'),
                'age': age,
                'city': city.get('title') if isinstance(city, dict) else None,
                'photo': candidate.get('photo_200'),
                'profile_url': f"https://vk.com/id{vk_id}",
                'verified': candidate.get('verified', False)
            })
            
            # Достаточно?
            if len(candidates) >= count:
                break
        
        return candidates
    
    def mark_as_viewed(self, current_user_id: int, candidate_id: int) -> bool:
        """Отмечает кандидата как просмотренного"""
        try:
            self.user_repo.add_to_view_history(current_user_id, candidate_id)
            return True
        except Exception as e:
            print(f"❌ Ошибка при сохранении в историю: {e}")
            return False
    
    def add_to_favorites(self, current_user_id: int, candidate_id: int) -> bool:
        """Добавляет кандидата в избранное"""
        try:
            self.user_repo.add_to_favorites(current_user_id, candidate_id)
            return True
        except Exception as e:
            print(f"❌ Ошибка при добавлении в избранное: {e}")
            return False
