import asyncio
import types
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .bot import DjangoBot


bot = DjangoBot()

@csrf_exempt
@require_POST
def webhook(request):
    """Обработчик вебхуков от Telegram"""
    try:
        update = json.loads(request.body)
        asyncio.run(bot.dp.feed_update(bot.bot, types.Update(**update)))
        return HttpResponse("OK")
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
