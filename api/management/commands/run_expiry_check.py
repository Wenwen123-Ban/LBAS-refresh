from django.core.management.base import BaseCommand
from api.expiry import run_expiry_check


class Command(BaseCommand):
    help = 'Run expiry check for transactions and user accounts'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting expiry check...'))
        
        try:
            run_expiry_check()
            self.stdout.write(self.style.SUCCESS('Expiry check completed successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during expiry check: {str(e)}'))
            raise
