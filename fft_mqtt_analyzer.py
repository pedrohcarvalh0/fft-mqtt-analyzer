#!/usr/bin/env python3
"""
Prencha os locais necessários com os dados do BROKER para que o programa execute da maneeira desejada

Exemplo:
        broker_host="192.168.0.103", broker_port=1883, username="admin", password="123456"):
"""

import paho.mqtt.client as mqtt
import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from collections import deque
import time
import threading
from matplotlib.animation import FuncAnimation
import queue

class CompactFFTAnalyzer:
    def __init__(self, broker_host="ENDEREÇO IP DO BROKER", broker_port=1883, username="USERNAME DEFINIDO NO BROKER", password="SENHA DEFINIDA NO BROKER"):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        
        # Criar cliente MQTT
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        if username and password:
            self.client.username_pw_set(username, password)
        
        # Buffers thread-safe
        self.temp_fft_queue = queue.Queue()
        self.humid_fft_queue = queue.Queue()
        self.temp_raw_queue = queue.Queue()
        self.humid_raw_queue = queue.Queue()
        
        # Buffers para plotagem
        self.temp_fft_data = deque(maxlen=50)
        self.humid_fft_data = deque(maxlen=50)
        self.temp_raw_data = deque(maxlen=100)
        self.humid_raw_data = deque(maxlen=100)
        self.timestamps = deque(maxlen=100)
        
        # Controle
        self.message_count = 0
        self.fft_message_count = 0
        self.last_message_time = time.time()
        self.is_connected = False
        self.data_lock = threading.Lock()
        
        # Callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        # Setup plots compacto
        self.setup_compact_plots()
        
    def setup_compact_plots(self):
        """Configura layout compacto com 4 gráficos principais"""
        self.fig = plt.figure(figsize=(16, 10))
        
        # Layout: 2x2 para dados principais + 2 pequenos para amplitude
        gs = self.fig.add_gridspec(3, 4, height_ratios=[2, 2, 1], hspace=0.3, wspace=0.3)
        
        # Gráficos principais (2x2 superior)
        self.ax1 = self.fig.add_subplot(gs[0, :2])  # Temperatura
        self.ax2 = self.fig.add_subplot(gs[0, 2:])  # Umidade
        self.ax3 = self.fig.add_subplot(gs[1, :2])  # FFT Temp Freq
        self.ax4 = self.fig.add_subplot(gs[1, 2:])  # FFT Humid Freq
        
        # Gráficos de amplitude (linha inferior)
        self.ax5 = self.fig.add_subplot(gs[2, :2])  # FFT Temp Amplitude
        self.ax6 = self.fig.add_subplot(gs[2, 2:])  # FFT Humid Amplitude
        
        self.fig.suptitle('Análise FFT Completa - DHT11 (RP2040)', fontsize=16, fontweight='bold')
        
        # Configurar títulos
        self.ax1.set_title('Temperatura (°C)', fontweight='bold')
        self.ax2.set_title('Umidade (%)', fontweight='bold')
        self.ax3.set_title('FFT Temperatura - Frequência', fontweight='bold')
        self.ax4.set_title('FFT Umidade - Frequência', fontweight='bold')
        self.ax5.set_title('FFT Temperatura - Amplitude', fontsize=10)
        self.ax6.set_title('FFT Umidade - Amplitude', fontsize=10)
        
        # Grid para todos
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4, self.ax5, self.ax6]:
            ax.grid(True, alpha=0.3)
    
    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"✅ Conectado ao broker MQTT!")
            self.is_connected = True
            
            topics = ["/temperature/fft", "/humidity/fft", "/temperature", "/humidity", "/online"]
            for topic in topics:
                client.subscribe(topic)
                print(f"📡 Subscrito: {topic}")
        else:
            print(f"❌ Falha na conexão MQTT: {rc}")
            self.is_connected = False
    
    def on_disconnect(self, client, userdata, rc, properties=None):
        self.is_connected = False
        print("🔌 Desconectado do MQTT")
    
    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            timestamp = datetime.now()
            
            self.message_count += 1
            self.last_message_time = time.time()
            
            if topic == "/temperature/fft":
                data = json.loads(payload)
                self.temp_fft_queue.put((data, timestamp))
                self.fft_message_count += 1
                print(f"🔬 FFT Temp - Freq: {data.get('freq', 0):.4f} Hz, Amp: {data.get('amplitude', 0):.2f}")
            
            elif topic == "/humidity/fft":
                data = json.loads(payload)
                self.humid_fft_queue.put((data, timestamp))
                self.fft_message_count += 1
                print(f"🔬 FFT Humid - Freq: {data.get('freq', 0):.4f} Hz, Amp: {data.get('amplitude', 0):.2f}")
            
            elif topic == "/temperature":
                temp_value = float(payload)
                self.temp_raw_queue.put((temp_value, timestamp))
                print(f"🌡️ Temp: {temp_value}°C")
            
            elif topic == "/humidity":
                humid_value = float(payload)
                self.humid_raw_queue.put((humid_value, timestamp))
                print(f"💧 Humid: {humid_value}%")
                
        except Exception as e:
            print(f"❌ Erro ao processar mensagem: {e}")
    
    def process_queues(self):
        """Processa filas de dados"""
        with self.data_lock:
            # Processar FFT temperatura
            while not self.temp_fft_queue.empty():
                try:
                    data, timestamp = self.temp_fft_queue.get_nowait()
                    self.temp_fft_data.append(data)
                    if len(self.timestamps) == 0 or timestamp > self.timestamps[-1]:
                        self.timestamps.append(timestamp)
                except queue.Empty:
                    break
            
            # Processar FFT umidade
            while not self.humid_fft_queue.empty():
                try:
                    data, timestamp = self.humid_fft_queue.get_nowait()
                    self.humid_fft_data.append(data)
                except queue.Empty:
                    break
            
            # Processar dados brutos
            while not self.temp_raw_queue.empty():
                try:
                    value, timestamp = self.temp_raw_queue.get_nowait()
                    self.temp_raw_data.append(value)
                except queue.Empty:
                    break
            
            while not self.humid_raw_queue.empty():
                try:
                    value, timestamp = self.humid_raw_queue.get_nowait()
                    self.humid_raw_data.append(value)
                except queue.Empty:
                    break
    
    def update_plots(self, frame):
        """Atualiza todos os gráficos"""
        self.process_queues()
        
        with self.data_lock:
            # Limpar gráficos
            for ax in [self.ax1, self.ax2, self.ax3, self.ax4, self.ax5, self.ax6]:
                ax.clear()
                ax.grid(True, alpha=0.3)
            
            current_time = datetime.now()
            
            # 1. Temperatura bruta
            if len(self.temp_raw_data) > 0:
                times = [current_time - timedelta(seconds=i*2) for i in range(len(self.temp_raw_data)-1, -1, -1)]
                self.ax1.plot(times, list(self.temp_raw_data), 'r-', marker='o', markersize=2, linewidth=2)
                self.ax1.set_title(f'Temperatura - {len(self.temp_raw_data)} amostras', fontweight='bold')
                self.ax1.set_ylabel('°C')
                
                avg_temp = np.mean(self.temp_raw_data)
                self.ax1.axhline(y=avg_temp, color='r', linestyle='--', alpha=0.7)
                self.ax1.text(0.02, 0.98, f'Média: {avg_temp:.1f}°C', transform=self.ax1.transAxes, 
                             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='mistyrose', alpha=0.8))
            
            # 2. Umidade bruta
            if len(self.humid_raw_data) > 0:
                times = [current_time - timedelta(seconds=i*2) for i in range(len(self.humid_raw_data)-1, -1, -1)]
                self.ax2.plot(times, list(self.humid_raw_data), 'b-', marker='s', markersize=2, linewidth=2)
                self.ax2.set_title(f'Umidade - {len(self.humid_raw_data)} amostras', fontweight='bold')
                self.ax2.set_ylabel('%')
                
                avg_humid = np.mean(self.humid_raw_data)
                self.ax2.axhline(y=avg_humid, color='b', linestyle='--', alpha=0.7)
                self.ax2.text(0.02, 0.98, f'Média: {avg_humid:.1f}%', transform=self.ax2.transAxes, 
                             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
            
            # 3. FFT Temperatura - Frequência
            if len(self.temp_fft_data) > 0:
                fft_times = list(self.timestamps)[-len(self.temp_fft_data):]
                temp_freqs = [d.get('freq', 0) for d in self.temp_fft_data]
                
                self.ax3.plot(fft_times, temp_freqs, 'g-', marker='^', markersize=3, linewidth=2)
                self.ax3.set_title(f'FFT Temperatura - Frequência ({len(self.temp_fft_data)} análises)', fontweight='bold')
                self.ax3.set_ylabel('Hz')
                
                if temp_freqs:
                    avg_freq = np.mean(temp_freqs)
                    self.ax3.axhline(y=avg_freq, color='g', linestyle='--', alpha=0.7)
                    
                    period_min = 1 / avg_freq / 60 if avg_freq > 0 else 0
                    self.ax3.text(0.02, 0.98, f'Freq: {avg_freq:.4f} Hz\nPeríodo: {period_min:.1f} min', 
                                 transform=self.ax3.transAxes, verticalalignment='top',
                                 bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
            
            # 4. FFT Umidade - Frequência
            if len(self.humid_fft_data) > 0:
                fft_times = list(self.timestamps)[-len(self.humid_fft_data):]
                humid_freqs = [d.get('freq', 0) for d in self.humid_fft_data]
                
                self.ax4.plot(fft_times, humid_freqs, 'm-', marker='d', markersize=3, linewidth=2)
                self.ax4.set_title(f'FFT Umidade - Frequência ({len(self.humid_fft_data)} análises)', fontweight='bold')
                self.ax4.set_ylabel('Hz')
                
                if humid_freqs:
                    avg_freq = np.mean(humid_freqs)
                    self.ax4.axhline(y=avg_freq, color='m', linestyle='--', alpha=0.7)
                    
                    period_min = 1 / avg_freq / 60 if avg_freq > 0 else 0
                    self.ax4.text(0.02, 0.98, f'Freq: {avg_freq:.4f} Hz\nPeríodo: {period_min:.1f} min', 
                                 transform=self.ax4.transAxes, verticalalignment='top',
                                 bbox=dict(boxstyle='round', facecolor='plum', alpha=0.8))
            
            # 5. FFT Temperatura - Amplitude
            if len(self.temp_fft_data) > 0:
                fft_times = list(self.timestamps)[-len(self.temp_fft_data):]
                temp_amps = [d.get('amplitude', 0) for d in self.temp_fft_data]
                
                self.ax5.plot(fft_times, temp_amps, 'orange', marker='o', markersize=3, linewidth=2)
                self.ax5.set_title('FFT Temperatura - Amplitude', fontsize=10)
                self.ax5.set_ylabel('Amplitude', fontsize=9)
                self.ax5.tick_params(labelsize=8)
                
                if temp_amps:
                    avg_amp = np.mean(temp_amps)
                    max_amp = max(temp_amps)
                    self.ax5.axhline(y=avg_amp, color='orange', linestyle='--', alpha=0.7)
                    self.ax5.text(0.02, 0.98, f'Média: {avg_amp:.2f}\nMáx: {max_amp:.2f}', 
                                 transform=self.ax5.transAxes, verticalalignment='top', fontsize=8,
                                 bbox=dict(boxstyle='round', facecolor='moccasin', alpha=0.8))
            
            # 6. FFT Umidade - Amplitude
            if len(self.humid_fft_data) > 0:
                fft_times = list(self.timestamps)[-len(self.humid_fft_data):]
                humid_amps = [d.get('amplitude', 0) for d in self.humid_fft_data]
                
                self.ax6.plot(fft_times, humid_amps, 'cyan', marker='s', markersize=3, linewidth=2)
                self.ax6.set_title('FFT Umidade - Amplitude', fontsize=10)
                self.ax6.set_ylabel('Amplitude', fontsize=9)
                self.ax6.tick_params(labelsize=8)
                
                if humid_amps:
                    avg_amp = np.mean(humid_amps)
                    max_amp = max(humid_amps)
                    self.ax6.axhline(y=avg_amp, color='cyan', linestyle='--', alpha=0.7)
                    self.ax6.text(0.02, 0.98, f'Média: {avg_amp:.2f}\nMáx: {max_amp:.2f}', 
                                 transform=self.ax6.transAxes, verticalalignment='top', fontsize=8,
                                 bbox=dict(boxstyle='round', facecolor='lightcyan', alpha=0.8))
            
            # Ajustar formatação dos eixos x para os gráficos menores
            for ax in [self.ax5, self.ax6]:
                ax.tick_params(axis='x', rotation=45, labelsize=8)
            
            plt.tight_layout()
    
    def start(self):
        """Inicia o analisador compacto"""
        print("🚀 Iniciando analisador FFT compacto...")
        
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # Animação
            ani = FuncAnimation(self.fig, self.update_plots, interval=1000, blit=False, cache_frame_data=False)
            
            print("✅ Analisador FFT compacto iniciado!")
            print("📊 Mostrando: Temperatura, Umidade, FFT Frequência e FFT Amplitude")
            print("🔄 Atualizando a cada 1 segundo")
            
            plt.show()
            
        except Exception as e:
            print(f"❌ Erro: {e}")
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            print("👋 Analisador finalizado!")

""" ALTERAR AS CREDENCIAS AQUI TAMBÉM """

if __name__ == "__main__":
    analyzer = CompactFFTAnalyzer(
        broker_host="ENDEREÇO IP DO BROKER",
        broker_port=1883,
        username="USERNAME DEFINIDO NO BROKER",
        password="SENHA DEFINIDA NO BROKER"
    )
    analyzer.start()
