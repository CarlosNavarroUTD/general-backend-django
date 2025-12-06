# apps/productos/management/commands/cargar_productos.py
import csv
from django.core.management.base import BaseCommand
from apps.productos.models import Producto, Marca, Tienda
from apps.teams.models import Team
from decimal import Decimal

class Command(BaseCommand):
    help = "Importa productos desde un CSV al catálogo"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Ruta al archivo CSV")

    def handle(self, *args, **kwargs):
        csv_file = kwargs["csv_file"]

        # Team por defecto
        try:
            team = Team.objects.get(id=1)
        except Team.DoesNotExist:
            self.stdout.write(self.style.ERROR("Team con ID=1 no existe"))
            return

        # Obtener o crear una tienda por defecto
        tienda, _ = Tienda.objects.get_or_create(
            nombre="Tienda Principal",
            team=team,
        )

        with open(csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Crear o obtener marca
                marca = None
                if row.get("Marca"):
                    marca, _ = Marca.objects.get_or_create(
                        nombre=row["Marca"].strip()
                    )

                # Precio seguro
                precio = row.get("Precio", "").replace(",", "").strip()
                precio = Decimal(precio) if precio else 0

                # Crear o actualizar producto
                Producto.objects.update_or_create(
                    nombre=row["Producto"].strip(),
                    sitio=tienda,
                    team=team,
                    defaults={
                        "marca": marca,
                        "categoria": row.get("Categoria", "otros").strip(),
                        "precio": precio,
                        "descripcion": row.get("Descripcion", "").strip(),
                    },
                )

        self.stdout.write(self.style.SUCCESS("Importación completada ✅"))
