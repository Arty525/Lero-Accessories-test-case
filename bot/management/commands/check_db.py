from django.core.management.base import BaseCommand
from django.db import connection
import os
from time import sleep


class Command(BaseCommand):
    help = 'Check database connection'

    def handle(self, *args, **options):
        self.stdout.write('Checking database connection...')
        self.stdout.write(f'DB_HOST: {os.getenv("DB_HOST")}')
        self.stdout.write(f'DB_NAME: {os.getenv("DB_NAME")}')
        self.stdout.write(f'DB_USER: {os.getenv("DB_USER")}')

        # Ждем пока база запустится
        for i in range(10):
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    self.stdout.write(
                        self.style.SUCCESS('✅ Database connection successful!')
                    )
                    return
            except Exception as e:
                self.stdout.write(f'Attempt {i + 1}: {e}')
                sleep(2)

        self.stdout.write(
            self.style.ERROR('❌ Failed to connect to database after 10 attempts')
        )