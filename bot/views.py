# views.py (обновленный с логированием)
import asyncio
import types
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .bot import DjangoBot

# Настройка логирования
logger = logging.getLogger(__name__)

bot = DjangoBot()


@csrf_exempt
@require_POST
def webhook(request):
    """Обработчик вебхуков от Telegram"""
    try:
        logger.info("Получен вебхук от Telegram")
        update = json.loads(request.body)

        # Логируем тип обновления
        if 'message' in update:
            logger.info(f"Получено сообщение от пользователя {update['message']['from']['id']}")
        elif 'callback_query' in update:
            logger.info(f"Получен callback от пользователя {update['callback_query']['from']['id']}")

        asyncio.run(bot.dp.feed_update(bot.bot, types.Update(**update)))
        logger.info("Вебхук успешно обработан")
        return HttpResponse("OK")

    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON: {e}")
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Критическая ошибка обработки вебхука: {e}")
        return JsonResponse({"error": str(e)}, status=400)