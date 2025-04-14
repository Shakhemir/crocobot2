import random
from src.settings import settings

set_of_words: set  # Список всех слов

with open(settings.WORDS_FILE, encoding="utf-8") as f:
    set_of_words = set(line.strip() for line in f if line.strip())


def get_random_word(game):
    """Возвращает случайное слово, исключая использованные"""

    if game.next_words:  # Если есть подкинутые админом слова
        word = game.next_words.pop(0)
        return word

    remaining_words = list(set_of_words - game.used_words)
    # Считаем сколько процентов слов не использовано.
    # Если менее 30%, то обнуляем множество использованных слов
    remain_per_cent = len(remaining_words) / len(set_of_words) < 0.3
    if not remain_per_cent:
        return random.choice(remaining_words)
    else:
        # Если использованные слова перекрывают все, то обнуляем это множество
        game.used_words.clear()
        return random.choice(list(set_of_words))
