async def obter_previsao_openmeteo(lat, lon, dias):
    url_wave = "https://marine-api.open-meteo.com/v1/marine"
    url_wind = "https://api.open-meteo.com/v1/forecast"
    start = dias[0].isoformat()
    end = dias[-1].isoformat()

    try:
        async with httpx.AsyncClient() as client:
            resp_wave = await client.get(url_wave, params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "wave_height,wave_direction",
                "timezone": "America/Sao_Paulo",
                "start_date": start,
                "end_date": end
            })

            resp_wind = await client.get(url_wind, params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "wind_speed_10m,wind_direction_10m",
                "timezone": "America/Sao_Paulo",
                "start_date": start,
                "end_date": end
            })

        resp_wave.raise_for_status()
        resp_wind.raise_for_status()

        dados_wave = resp_wave.json()
        dados_wind = resp_wind.json()
        previsoes = []

        for dia in dias:
            data_str = dia.isoformat()

            horarios = dados_wave["hourly"]["time"]
            alturas = dados_wave["hourly"]["wave_height"]
            direcoes = dados_wave["hourly"]["wave_direction"]
            ventos = dados_wind["hourly"]["wind_speed_10m"]
            vento_dir = dados_wind["hourly"]["wind_direction_10m"]

            indices = [i for i, h in enumerate(horarios) if h.startswith(data_str)]
            if not indices:
                continue

            melhor_hora, max_altura = "", 0
            for i in indices:
                if alturas[i] > max_altura:
                    max_altura = alturas[i]
                    melhor_hora = horarios[i][11:16]

            i_best = indices[alturas.index(max_altura)]

            # Estrelas com base apenas na altura da onda
            estrelas_num = int(min(max_altura * 2, 5))
            estrelas = "⭐️" * estrelas_num

            # Comentário baseado nas estrelas
            if estrelas_num <= 2:
                comentario = "Condição fraca para o pico"
            elif estrelas_num == 3:
                comentario = "Condição regular, com potencial"
            else:
                comentario = "Boa condição para o pico"

            previsoes.append({
                "data": dia.strftime("%d/%m/%Y"),
                "melhor_horario": melhor_hora,
                "onda": round(alturas[i_best], 1),
                "direcao_onda": int(direcoes[i_best]),
                "vento": int(ventos[i_best]),
                "direcao_vento": int(vento_dir[i_best]),
                "estrelas": estrelas,
                "comentario": comentario
            })

        return previsoes

    except Exception as e:
        print("❌ Erro na API Open-Meteo:", e)
        print(traceback.format_exc())
        return None
