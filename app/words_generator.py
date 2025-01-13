import random
from src.settings import settings
from src.game import Game

set_of_words: set  # Список всех слов

with open(settings.WORDS_FILE, encoding="utf-8") as f:
    set_of_words = set(line.strip() for line in f if line.strip())
    print(set_of_words)


def get_random_word(game: Game):
    """Возвращает случайное слово, исключая использованные"""
    remaining_words = list(set_of_words - game.used_words)
    if remaining_words:
        return random.choice(remaining_words)
    else:
        # Если использованные слова перекрывают все, то обнуляем это множество
        game.used_words.clear()
        return random.choice(list(set_of_words))
