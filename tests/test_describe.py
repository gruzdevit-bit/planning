from app.describe import describe


def test_describe_equals_task_title():
    assert describe() == (
        "Необходимо разработать программу ежедневник где я буду планировать "
        "дела на каждый день, там должен быть календать , планировщик дел, "
        "просмотр новостей с сайта lenta.ru интерфейс до"
    )
