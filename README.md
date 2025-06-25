
# Projeto: Analisador de FFT MQTT em Python

## Descrição

Este código Python recebe os dados publicados pelo RP2040 via MQTT, realiza o processamento, armazena e plota gráficos dinâmicos para análise das séries temporais e das FFTs de temperatura e umidade.

## Pré-requisitos
- **Broker MQTT**: Um broker ativo (exemplo: Mosquitto)
- **Configuração do broker**: https://youtu.be/UmmK6MiXOqM?si=WFZpqj1_aV5oBVlE
- **Python 3.x**
- **Bibliotecas Python necessárias:**

```bash
pip install paho-mqtt matplotlib numpy pandas
```

## Configuração obrigatória

No início do arquivo `fft_mqtt_analyzer.py`, altere os parâmetros de conexão:

```python
analyzer = CompactFFTAnalyzer(
    broker_host="ENDEREÇO IP DO BROKER",
    broker_port=1883,
    username="USERNAME DEFINIDO NO BROKER",
    password="SENHA DEFINIDA NO BROKER"
)
```

Use o mesmo IP e credenciais do seu Broker (exemplo: `192.168.0.xxx`).

## Tópicos MQTT que o script assina

| Tópico | Conteúdo |
|---|---|
| `/temperature` | Temperatura (float) |
| `/humidity` | Umidade (float) |
| `/temperature/fft` | JSON com frequência e amplitude da temperatura |
| `/humidity/fft` | JSON com frequência e amplitude da umidade |
| `/online` | Status de conexão |

## Recursos exibidos

- Gráfico da **Temperatura em tempo real**
- Gráfico da **Umidade em tempo real**
- Gráfico de **Frequência Dominante da FFT da Temperatura**
- Gráfico de **Frequência Dominante da FFT da Umidade**
- Gráficos de **Amplitude da FFT** para ambos os sinais

## Execução

```bash
python fft_mqtt_analyzer.py
```

A interface gráfica abrirá com atualização automática dos gráficos a cada segundo.
