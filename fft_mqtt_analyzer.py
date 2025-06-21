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

class FFTAnalyzer:
    def __init__(self, broker_host="192.168.0.103", broker_port=1883, username="admin", password="123456"):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        
        # Criar cliente MQTT com callback API version 2
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        
        # Configurar credenciais de autenticação
        if username and password:
            self.client.username_pw_set(username, password)
            print(f"🔐 Configuradas credenciais: {username}/{'*' * len(password)}")
        
        # Buffers para armazenar dados (thread-safe usando queue)
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
        
        # Contadores para debug
        self.message_count = 0
        self.fft_message_count = 0
        self.last_message_time = time.time()
        self.connection_attempts = 0
        self.is_connected = False
        
        # Lock para thread safety
        self.data_lock = threading.Lock()
        
        # Configurar callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        # Configurar matplotlib
        plt.style.use('default')
        self.setup_plots()
        
    def setup_plots(self):
        """Configura os gráficos matplotlib"""
        self.fig, ((self.ax1, self.ax2), (self.ax3, self.ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        self.fig.suptitle('Análise FFT em Tempo Real - DHT11 (RP2040)', fontsize=14, fontweight='bold')
        
        # Configurar cada subplot
        self.ax1.set_title('Temperatura (°C)')
        self.ax1.set_ylabel('Temperatura (°C)')
        self.ax1.grid(True, alpha=0.3)
        
        self.ax2.set_title('Umidade (%)')
        self.ax2.set_ylabel('Umidade (%)')
        self.ax2.grid(True, alpha=0.3)
        
        self.ax3.set_title('FFT Temperatura - Frequência Dominante')
        self.ax3.set_ylabel('Frequência (Hz)')
        self.ax3.grid(True, alpha=0.3)
        
        self.ax4.set_title('FFT Umidade - Frequência Dominante')
        self.ax4.set_ylabel('Frequência (Hz)')
        self.ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
    def on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback de conexão MQTT"""
        self.connection_attempts += 1
        
        if rc == 0:
            print(f"✅ Conectado ao broker MQTT! (tentativa {self.connection_attempts})")
            print(f"🔗 Broker: {self.broker_host}:{self.broker_port}")
            self.is_connected = True
            
            # Subscrever aos tópicos necessários
            topics = [
                "/temperature/fft",
                "/humidity/fft", 
                "/temperature",
                "/humidity",
                "/online"
            ]
            
            for topic in topics:
                result = client.subscribe(topic)
                print(f"📡 Subscrito ao tópico: {topic} (resultado: {result})")
                
        else:
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier", 
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorized"
            }
            
            error_msg = error_messages.get(rc, f"Unknown error code: {rc}")
            print(f"❌ Falha na conexão MQTT: {error_msg}")
            self.is_connected = False
            
    def on_disconnect(self, client, userdata, rc, properties=None):
        """Callback de desconexão MQTT"""
        self.is_connected = False
        if rc != 0:
            print(f"🔌 Desconexão inesperada do broker MQTT. Código: {rc}")
        else:
            print("🔌 Desconectado do broker MQTT")
        
    def on_message(self, client, userdata, msg):
        """Callback para mensagens MQTT recebidas"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            timestamp = datetime.now()
            
            self.message_count += 1
            self.last_message_time = time.time()
            
            print(f"📨 [{self.message_count}] {timestamp.strftime('%H:%M:%S')} - {topic}: {payload}")
            
            # Processar mensagens baseado no tópico
            if topic == "/temperature/fft":
                try:
                    data = json.loads(payload)
                    self.temp_fft_queue.put((data, timestamp))
                    self.fft_message_count += 1
                    print(f"🔬 FFT Temp - Freq: {data.get('freq', 0):.4f} Hz, Amp: {data.get('amplitude', 0):.2f}")
                except json.JSONDecodeError as e:
                    print(f"❌ Erro JSON em /temperature/fft: {e}")
            
            elif topic == "/humidity/fft":
                try:
                    data = json.loads(payload)
                    self.humid_fft_queue.put((data, timestamp))
                    self.fft_message_count += 1
                    print(f"🔬 FFT Humid - Freq: {data.get('freq', 0):.4f} Hz, Amp: {data.get('amplitude', 0):.2f}")
                except json.JSONDecodeError as e:
                    print(f"❌ Erro JSON em /humidity/fft: {e}")
            
            elif topic == "/temperature":
                try:
                    temp_value = float(payload)
                    self.temp_raw_queue.put((temp_value, timestamp))
                    print(f"🌡️ Temperatura: {temp_value}°C")
                except ValueError as e:
                    print(f"❌ Erro ao converter temperatura: {e}")
            
            elif topic == "/humidity":
                try:
                    humid_value = float(payload)
                    self.humid_raw_queue.put((humid_value, timestamp))
                    print(f"💧 Umidade: {humid_value}%")
                except ValueError as e:
                    print(f"❌ Erro ao converter umidade: {e}")
            
            elif topic == "/online":
                print(f"🟢 RP2040 Status: {payload}")
            
        except Exception as e:
            print(f"❌ Erro ao processar mensagem: {e}")
    
    def process_queues(self):
        """Processa as filas de dados de forma thread-safe"""
        with self.data_lock:
            # Processar dados FFT de temperatura
            while not self.temp_fft_queue.empty():
                try:
                    data, timestamp = self.temp_fft_queue.get_nowait()
                    self.temp_fft_data.append(data)
                    if len(self.timestamps) == 0 or timestamp > self.timestamps[-1]:
                        self.timestamps.append(timestamp)
                except queue.Empty:
                    break
            
            # Processar dados FFT de umidade
            while not self.humid_fft_queue.empty():
                try:
                    data, timestamp = self.humid_fft_queue.get_nowait()
                    self.humid_fft_data.append(data)
                except queue.Empty:
                    break
            
            # Processar dados brutos de temperatura
            while not self.temp_raw_queue.empty():
                try:
                    value, timestamp = self.temp_raw_queue.get_nowait()
                    self.temp_raw_data.append(value)
                except queue.Empty:
                    break
            
            # Processar dados brutos de umidade
            while not self.humid_raw_queue.empty():
                try:
                    value, timestamp = self.humid_raw_queue.get_nowait()
                    self.humid_raw_data.append(value)
                except queue.Empty:
                    break
    
    def update_plots(self, frame):
        """Atualiza os gráficos (chamado pela animação)"""
        self.process_queues()
        
        with self.data_lock:
            # Limpar todos os gráficos
            for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
                ax.clear()
            
            current_time = datetime.now()
            
            # Gráfico 1: Temperatura bruta
            if len(self.temp_raw_data) > 0:
                times = [current_time - timedelta(seconds=i*2) for i in range(len(self.temp_raw_data)-1, -1, -1)]
                self.ax1.plot(times, list(self.temp_raw_data), 'r-', marker='o', markersize=3, linewidth=2, label='Temperatura')
                self.ax1.set_title(f'Temperatura - {len(self.temp_raw_data)} amostras')
                self.ax1.set_ylabel('Temperatura (°C)')
                self.ax1.grid(True, alpha=0.3)
                self.ax1.tick_params(axis='x', rotation=45)
                if len(self.temp_raw_data) > 1:
                    self.ax1.set_ylim(min(self.temp_raw_data) - 1, max(self.temp_raw_data) + 1)
            else:
                self.ax1.text(0.5, 0.5, 'Aguardando dados de temperatura...', 
                             ha='center', va='center', transform=self.ax1.transAxes)
                self.ax1.set_title('Temperatura (sem dados)')
            
            # Gráfico 2: Umidade bruta
            if len(self.humid_raw_data) > 0:
                times = [current_time - timedelta(seconds=i*2) for i in range(len(self.humid_raw_data)-1, -1, -1)]
                self.ax2.plot(times, list(self.humid_raw_data), 'b-', marker='s', markersize=3, linewidth=2, label='Umidade')
                self.ax2.set_title(f'Umidade - {len(self.humid_raw_data)} amostras')
                self.ax2.set_ylabel('Umidade (%)')
                self.ax2.grid(True, alpha=0.3)
                self.ax2.tick_params(axis='x', rotation=45)
                if len(self.humid_raw_data) > 1:
                    self.ax2.set_ylim(min(self.humid_raw_data) - 5, max(self.humid_raw_data) + 5)
            else:
                self.ax2.text(0.5, 0.5, 'Aguardando dados de umidade...', 
                             ha='center', va='center', transform=self.ax2.transAxes)
                self.ax2.set_title('Umidade (sem dados)')
            
            # Gráfico 3: FFT Temperatura
            if len(self.temp_fft_data) > 0:
                fft_times = list(self.timestamps)[-len(self.temp_fft_data):]
                temp_freqs = [d.get('freq', 0) for d in self.temp_fft_data]
                temp_amps = [d.get('amplitude', 0) for d in self.temp_fft_data]
                
                # Plotar frequência
                self.ax3.plot(fft_times, temp_freqs, 'g-', marker='^', markersize=4, linewidth=2, label='Frequência')
                self.ax3.set_title(f'FFT Temperatura - {len(self.temp_fft_data)} análises')
                self.ax3.set_ylabel('Frequência (Hz)')
                self.ax3.grid(True, alpha=0.3)
                self.ax3.tick_params(axis='x', rotation=45)
                
                # Adicionar informação da amplitude como texto
                if temp_freqs:
                    avg_freq = np.mean(temp_freqs)
                    avg_amp = np.mean(temp_amps)
                    self.ax3.text(0.02, 0.98, f'Freq média: {avg_freq:.4f} Hz\nAmp média: {avg_amp:.2f}', 
                                 transform=self.ax3.transAxes, verticalalignment='top',
                                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            else:
                progress_text = f'Aguardando análise FFT...\nMensagens FFT: {self.fft_message_count}'
                self.ax3.text(0.5, 0.5, progress_text, 
                             ha='center', va='center', transform=self.ax3.transAxes)
                self.ax3.set_title('FFT Temperatura (aguardando)')
            
            # Gráfico 4: FFT Umidade
            if len(self.humid_fft_data) > 0:
                fft_times = list(self.timestamps)[-len(self.humid_fft_data):]
                humid_freqs = [d.get('freq', 0) for d in self.humid_fft_data]
                humid_amps = [d.get('amplitude', 0) for d in self.humid_fft_data]
                
                # Plotar frequência
                self.ax4.plot(fft_times, humid_freqs, 'm-', marker='d', markersize=4, linewidth=2, label='Frequência')
                self.ax4.set_title(f'FFT Umidade - {len(self.humid_fft_data)} análises')
                self.ax4.set_ylabel('Frequência (Hz)')
                self.ax4.grid(True, alpha=0.3)
                self.ax4.tick_params(axis='x', rotation=45)
                
                # Adicionar informação da amplitude como texto
                if humid_freqs:
                    avg_freq = np.mean(humid_freqs)
                    avg_amp = np.mean(humid_amps)
                    self.ax4.text(0.02, 0.98, f'Freq média: {avg_freq:.4f} Hz\nAmp média: {avg_amp:.2f}', 
                                 transform=self.ax4.transAxes, verticalalignment='top',
                                 bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
            else:
                progress_text = f'Aguardando análise FFT...\nMensagens FFT: {self.fft_message_count}'
                self.ax4.text(0.5, 0.5, progress_text, 
                             ha='center', va='center', transform=self.ax4.transAxes)
                self.ax4.set_title('FFT Umidade (aguardando)')
            
            # Ajustar layout
            plt.tight_layout()
    
    def show_status(self):
        """Mostra status atual do sistema"""
        current_time = time.time()
        time_since_last = current_time - self.last_message_time
        
        print("\n" + "="*60)
        print("📊 STATUS DO SISTEMA")
        print("="*60)
        print(f"🔗 Broker MQTT: {self.broker_host}:{self.broker_port}")
        print(f"👤 Usuário: {self.username}")
        print(f"🔄 Tentativas de conexão: {self.connection_attempts}")
        print(f"🟢 Conectado: {'SIM' if self.is_connected else 'NÃO'}")
        print(f"📨 Total de mensagens: {self.message_count}")
        print(f"🔬 Mensagens FFT: {self.fft_message_count}")
        print(f"🌡️ Amostras temperatura: {len(self.temp_raw_data)}")
        print(f"💧 Amostras umidade: {len(self.humid_raw_data)}")
        print(f"⏰ Última mensagem: {time_since_last:.1f}s atrás")
        
        if time_since_last > 30:
            print("⚠️ ATENÇÃO: Não há mensagens há mais de 30 segundos!")
            print("   Verifique se o RP2040 está funcionando.")
        
        if self.message_count == 0:
            print("❌ PROBLEMA: Nenhuma mensagem MQTT recebida!")
            print("   Possíveis causas:")
            print("   1. RP2040 não está conectado ao WiFi")
            print("   2. RP2040 não está conectado ao broker MQTT")
            print("   3. Credenciais incorretas")
            print("   4. Broker MQTT não está rodando")
        
        print("="*60)
    
    def export_data(self, filename=None):
        """Exporta dados para CSV"""
        if not self.temp_raw_data and not self.temp_fft_data:
            print("❌ Nenhum dado para exportar")
            return
            
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fft_data_{timestamp}.csv"
        
        data = []
        max_len = max(len(self.temp_raw_data), len(self.temp_fft_data), len(self.humid_raw_data), len(self.humid_fft_data))
        
        for i in range(max_len):
            row = {'index': i, 'timestamp': datetime.now() - timedelta(seconds=i*2)}
            
            if i < len(self.temp_raw_data):
                row['temp_raw'] = self.temp_raw_data[i]
            if i < len(self.humid_raw_data):
                row['humid_raw'] = self.humid_raw_data[i]
            if i < len(self.temp_fft_data):
                fft_data = self.temp_fft_data[i]
                row['temp_freq'] = fft_data.get('freq', 0)
                row['temp_amplitude'] = fft_data.get('amplitude', 0)
                row['temp_period_min'] = fft_data.get('period_min', 0)
            if i < len(self.humid_fft_data):
                fft_data = self.humid_fft_data[i]
                row['humid_freq'] = fft_data.get('freq', 0)
                row['humid_amplitude'] = fft_data.get('amplitude', 0)
                row['humid_period_min'] = fft_data.get('period_min', 0)
                
            data.append(row)
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        print(f"💾 Dados exportados para {filename}")
        print(f"📊 {len(data)} linhas exportadas")
    
    def start(self):
        """Inicia o analisador"""
        print("🚀 Iniciando analisador FFT...")
        
        try:
            # Conectar ao MQTT
            print("📡 Conectando ao broker MQTT...")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # Configurar animação matplotlib
            print("📊 Configurando gráficos...")
            ani = FuncAnimation(self.fig, self.update_plots, interval=1000, blit=False, cache_frame_data=False)
            
            print("\n" + "="*60)
            print("✅ ANALISADOR FFT INICIADO!")
            print("="*60)
            print("Comandos disponíveis na janela do terminal:")
            print("  's' + Enter: Mostrar status")
            print("  'e' + Enter: Exportar dados")
            print("  'q' + Enter: Sair")
            print("  Feche a janela do gráfico para sair")
            print("="*60)
            
            # Thread para comandos do usuário
            def command_thread():
                while True:
                    try:
                        cmd = input("Digite um comando (s/e/q): ").strip().lower()
                        if cmd == 's':
                            self.show_status()
                        elif cmd == 'e':
                            self.export_data()
                        elif cmd == 'q':
                            plt.close('all')
                            break
                        elif cmd == '':
                            continue
                        else:
                            print("Comando inválido. Use: s, e, ou q")
                    except (KeyboardInterrupt, EOFError):
                        plt.close('all')
                        break
            
            # Iniciar thread de comandos
            cmd_thread = threading.Thread(target=command_thread, daemon=True)
            cmd_thread.start()
            
            # Mostrar gráficos (bloqueia até fechar a janela)
            plt.show()
            
        except Exception as e:
            print(f"❌ Erro: {e}")
        finally:
            print("🛑 Parando analisador...")
            self.client.loop_stop()
            self.client.disconnect()
            print("👋 Analisador FFT finalizado!")

if __name__ == "__main__":
    # Configurar com as mesmas credenciais do RP2040
    analyzer = FFTAnalyzer(
        broker_host="192.168.0.103",
        broker_port=1883,
        username="admin", 
        password="123456"
    )
    analyzer.start()
