import httpx
from datetime import date, timedelta

# Coordenadas de Itaúna – Saquarema
latitude = -22.93668
longitude = -42.48337

# Datas de hoje até 2 dias depois
hoje = date.today()
fim = hoje + timedelta(days=2)

# URL e parâmetros
url = "https://marine-api.open-meteo.com/v1/marine"
params = {
    "latitude": latitude,
    "longitude": longitude,
    "hourly": "wave_height,wave_direction,wind_wave_height,wind_wave_direction,wind_speed,wind_direction",
    "start_date": hoje.isoformat(),
    "end_date": fim.isoformat(),
    "timezone": "auto"
}

try:
    response = httpx.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    print("✅ Previsão recebida com sucesso!")
    print("Horários:", data["hourly"]["time"][:5])
    print("Altura das ondas (m):", data["hourly"]["wave_height"][:5])
    print("Direção das ondas (°):", data["hourly"]["wave_direction"][:5])
    print("Altura das ondas de vento (m):", data["hourly"]["wind_wave_height"][:5])
    print("Direção das ondas de vento (°):", data["hourly"]["wind_wave_direction"][:5])
    print("Vento (km/h):", data["hourly"]["wind_speed"][:5])
    print("Direção do vento (°):", data["hourly"]["wind_direction"][:5])

except Exception as e:
    print("❌ Erro ao consultar API Open-Meteo:")
    print(e)
