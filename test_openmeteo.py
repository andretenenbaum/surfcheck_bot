import httpx
from datetime import date, timedelta

# Coordenadas do pico de Itaúna – Saquarema
latitude = -22.93668
longitude = -42.48337

# Datas de início e fim da previsão
hoje = date.today()
fim = hoje + timedelta(days=2)

# URL da API e parâmetros
url = "https://marine-api.open-meteo.com/v1/marine"
params = {
    "latitude": latitude,
    "longitude": longitude,
    "hourly": "wave_height,wave_direction,wind_speed,wind_direction",
    "timezone": "America/Sao_Paulo",
    "start_date": hoje.isoformat(),
    "end_date": fim.isoformat()
}

# Requisição à API
try:
    response = httpx.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    # Exibição de amostra dos dados
    print("✅ Previsão recebida com sucesso!")
    print("Horários:", data["hourly"]["time"][:5])
    print("Altura das ondas (m):", data["hourly"]["wave_height"][:5])
    print("Direção das ondas (°):", data["hourly"]["wave_direction"][:5])
    print("Vento (km/h):", data["hourly"]["wind_speed"][:5])
    print("Direção do vento (°):", data["hourly"]["wind_direction"][:5])

except Exception as e:
    print("❌ Erro ao consultar API Open-Meteo:")
    print(e)
