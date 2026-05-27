from django.core.management.base import BaseCommand

from detection.services.ml_bridge import MLBridge


class Command(BaseCommand):
    help = "Load combined_meta.pkl from ml_service into CellModel DB records"

    def add_arguments(self, parser):
        parser.add_argument(
            "--model-dir",
            type=str,
            default=None,
            help="Override model directory (defaults to ML_MODEL_DIR in settings)",
        )

    def handle(self, *args, **options):
        bridge = MLBridge()
        model_dir = options["model_dir"]
        self.stdout.write("Syncing cell models from combined_meta.pkl ...")
        bridge._sync_cell_models(model_dir)
        from detection.models import CellModel
        count = CellModel.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Done. {count} cell models in DB."))
