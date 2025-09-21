# cron.py
from datetime import datetime, time
from django.utils import timezone
from . import models
from app import models as app_models
from .zimra import close_day
import logging

logger = logging.getLogger(__name__)


def auto_close_fiscal_day():
    """
    Auto close fiscal day for all ZimraConfigs
    Gets invoices from start of day until 21:00 and calls close_day function
    """
    try:
        # Get today's date
        today = timezone.now().date()

        # Create datetime for 21:00 today
        cutoff_time = datetime.combine(today, time(21, 0))  # 21:00 (9 PM)

        print(f"Starting auto fiscal day closure for {today} up to 21:00")
        logger.info(f"Starting auto fiscal day closure for {today} up to 21:00")

        # Get all active ZimraConfigs (active when zimra_api_device_information is set)
        zimra_configs = models.ZimraConfig.objects.filter(
            zimra_api_device_information__isnull=False
        ).exclude(zimra_api_device_information={})

        if not zimra_configs.exists():
            print("No active ZimraConfigs found")
            logger.warning("No active ZimraConfigs found")
            return

        print(f"Found {zimra_configs.count()} active ZimraConfig(s)")

        # Process each ZimraConfig
        for config in zimra_configs:
            try:
                print(f"Processing ZimraConfig ID: {config.id} for {config.organisation.name}")

                # Get invoices for this config's organisation from start of day until 21:00
                invoices = app_models.Invoice.objects.filter(
                    connected_app__organisation=config.organisation,
                    created__date=today,
                    created__lte=cutoff_time,
                    status__in=['submitted', 'fiscalised']  # Process both submitted and fiscalised invoices
                ).order_by('created')

                print(f"Found {invoices.count()} invoices for {config.organisation.name}")
                logger.info(f"Found {invoices.count()} invoices for {config.organisation.name}")

                # Call the close_day function
                result = close_day(config, list(invoices))

                if result:
                    success_msg = f"Successfully closed fiscal day for {config.organisation.name} (ZimraConfig ID: {config.id})"
                    print(success_msg)
                    logger.info(success_msg)
                else:
                    error_msg = f"Failed to close fiscal day for {config.organisation.name} (ZimraConfig ID: {config.id})"
                    print(error_msg)
                    logger.error(error_msg)

            except Exception as e:
                error_msg = f"Error processing ZimraConfig {config.id} for {config.organisation.name}: {str(e)}"
                print(error_msg)
                logger.error(error_msg, exc_info=True)
                # Continue with next config instead of stopping
                continue

        print("Auto fiscal day closure completed")
        logger.info("Auto fiscal day closure completed")

    except Exception as e:
        error_msg = f"Error in auto_close_fiscal_day: {str(e)}"
        print(error_msg)
        logger.error(error_msg, exc_info=True)