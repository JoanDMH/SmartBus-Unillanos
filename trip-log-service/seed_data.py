import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone
from storage.database import async_sessionmaker, engine, TripRow, init_db

# 10 Perfiles de prueba
PROFILES = [
    {"name": "Carlos Mendoza", "route": "PARQUE", "bus": "BUS-101"},
    {"name": "Ana Silva", "route": "PARQUE", "bus": "BUS-102"},
    {"name": "Juan Castro", "route": "PARQUE", "bus": "BUS-103"},
    {"name": "Diana Morales", "route": "PARQUE", "bus": "BUS-104"},
    {"name": "Luis Peña", "route": "PARQUE", "bus": "BUS-105"},
    {"name": "Martha Gomez", "route": "PARQUE", "bus": "BUS-106"},
    {"name": "Jorge Ortiz", "route": "PARQUE", "bus": "BUS-107"},
    {"name": "Elena Erazo", "route": "PARQUE", "bus": "BUS-108"},
    {"name": "Pedro Infante", "route": "PARQUE", "bus": "BUS-109"},
    {"name": "Lucia Reyes", "route": "PARQUE", "bus": "BUS-110"},
]

WEATHERS = ["SOLEADO", "NUBLADO", "LLUVIOSO"]

async def seed():
    print("Iniciando generador de datos...")
    
    # Asegurar que las tablas existan en PostgreSQL
    await init_db()
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    async with SessionLocal() as session:
        now = datetime.now(timezone.utc)
        trips_to_add = []

        for profile in PROFILES:
            # 60 registros por perfil para justificar mes y medio de recolección
            for i in range(60):
                # Distribuir los viajes aleatoriamente en los últimos 45 días
                days_ago = random.randint(0, 45)
                
                # Simular patrones reales de comportamiento
                if i % 2 == 0:
                    # Viajes de mañana (Hora pico - Alta demanda)
                    hour = random.randint(6, 8)
                    passengers = random.randint(35, 60)
                    notes = "Alta afluencia estudiantil en la mañana."
                else:
                    # Viajes de mediodía/tarde (Demanda moderada)
                    hour = random.randint(12, 17)
                    passengers = random.randint(15, 35)
                    notes = "Flujo normal de pasajeros."

                # Ajustar la fecha y hora de salida
                departure = now - timedelta(days=days_ago)
                departure = departure.replace(hour=hour, minute=random.choice([0, 20, 40]), second=0, microsecond=0)

                trip = TripRow(
                    id=str(uuid.uuid4()),
                    route_id=profile["route"],
                    bus_id=profile["bus"],
                    departure_time=departure,
                    passenger_count=passengers,
                    weather=random.choice(WEATHERS),
                    academic_week=random.randint(1, 16),
                    special_event=random.random() < 0.05, # 5% de probabilidad de evento especial
                    notes=notes,
                    registered_by=profile["name"],
                    created_at=now
                )
                trips_to_add.append(trip)
        
        session.add_all(trips_to_add)
        await session.commit()
        print(f"¡Misión cumplida! Se han insertado {len(trips_to_add)} viajes reales en PostgreSQL.")

if __name__ == "__main__":
    asyncio.run(seed())