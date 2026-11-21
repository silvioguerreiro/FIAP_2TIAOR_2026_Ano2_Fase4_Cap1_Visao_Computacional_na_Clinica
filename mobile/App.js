// CardioIA Fase 4, Ir Alem 2: app React Native (Expo) que envia uma radiografia de torax
// ao backend Flask e exibe a categoria detectada pela CNN.
// Prototipo academico, sem validade diagnostica.
import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator, Image, Platform, Pressable, SafeAreaView, ScrollView,
  StatusBar, StyleSheet, Text, TextInput, View,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';

// No emulador Android, o computador que roda o Flask e visto como 10.0.2.2.
// No simulador iOS e no navegador, 127.0.0.1 funciona. Em celular fisico, use o IP do computador na rede.
const API_PADRAO = Platform.OS === 'android' ? 'http://10.0.2.2:5050'
  : Platform.OS === 'web' ? `http://${window.location.hostname}:5050`   // mesmo host em que a pagina foi aberta
  : 'http://127.0.0.1:5050';

const CORES = {
  azul: '#1f3864', fundo: '#f4f6f9', borda: '#d8dee8', cinza: '#5b6472',
  baixa: '#2e7d32', intermediaria: '#b26a00', alta: '#c62828',
};

export default function App() {
  const [api, setApi] = useState(API_PADRAO);
  const [info, setInfo] = useState(null);
  const [imagem, setImagem] = useState(null);      // uri para exibir
  const [resultado, setResultado] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);
  const [mostrarConfig, setMostrarConfig] = useState(false);
  const rolagem = useRef(null);          // ScrollView principal
  const yResultado = useRef(null);       // posicao vertical do cartao de resultado
  const rolarPendente = useRef(false);

  // Quando uma analise comeca, leva a tela ate o cartao de resultado (ele fica abaixo da area visivel)
  const rolarParaResultado = () => {
    if (rolagem.current && yResultado.current !== null) {
      rolagem.current.scrollTo({ y: Math.max(yResultado.current - 8, 0), animated: true });
      rolarPendente.current = false;
    }
  };
  useEffect(() => {
    if (carregando) { rolarPendente.current = true; rolarParaResultado(); }
  }, [carregando]);

  // Busca limites, metricas e lista de exemplos no backend
  const conectar = async (base) => {
    setErro(null);
    try {
      const r = await fetch(`${base}/api/info`);
      if (!r.ok) throw new Error();
      setInfo(await r.json());
    } catch (e) {
      setInfo(null);
      setErro(`Não foi possível conectar ao servidor em ${base}. Verifique se o backend Flask está em execução.`);
    }
  };
  useEffect(() => { conectar(api); }, []);

  // Falha de rede chega com mensagens diferentes no navegador e no celular; as demais vem do backend, em portugues
  const mensagemDeErro = (e) => (e.message === 'Network request failed' || e.message === 'Failed to fetch'
    ? 'Sem conexão com o servidor. Verifique o endereço do backend.' : e.message);

  const tratarResposta = async (r) => {
    const dados = await r.json();
    if (!r.ok) throw new Error(dados.erro || 'O servidor não conseguiu analisar a imagem.');
    setResultado(dados);
  };

  const analisarArquivo = async (asset) => {
    setImagem(asset.uri); setResultado(null); setErro(null); setCarregando(true);
    try {
      const form = new FormData();
      if (Platform.OS === 'web') {
        // no navegador o seletor devolve um File; se nao houver, converte a uri em blob
        const arquivo = asset.file || await (await fetch(asset.uri)).blob();
        form.append('imagem', arquivo, asset.fileName || 'radiografia.jpg');
      } else {
        form.append('imagem', { uri: asset.uri, name: asset.fileName || 'radiografia.jpg', type: asset.mimeType || 'image/jpeg' });
      }
      await tratarResposta(await fetch(`${api}/api/predict`, { method: 'POST', body: form }));
    } catch (e) { setErro(mensagemDeErro(e)); } finally { setCarregando(false); }
  };

  const escolherDaGaleria = async () => {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) { setErro('Permissão de acesso às imagens negada.'); return; }
    const r = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 1 });
    if (!r.canceled) analisarArquivo(r.assets[0]);
  };

  const analisarExemplo = async (nome) => {
    setImagem(`${api}/static/exemplos/${nome}`); setResultado(null); setErro(null); setCarregando(true);
    try {
      await tratarResposta(await fetch(`${api}/api/exemplo/${nome}`));
    } catch (e) { setErro(mensagemDeErro(e)); } finally { setCarregando(false); }
  };

  const pct = (v) => `${Math.round(v * 100)}%`;
  const cor = resultado ? CORES[resultado.faixa] : CORES.azul;

  return (
    <SafeAreaView style={s.tela}>
      <StatusBar barStyle="light-content" backgroundColor={CORES.azul} />
      <View style={s.topo}>
        <Text style={s.titulo}>CardioIA</Text>
        <Text style={s.subtitulo}>Assistente Cardiológico Virtual</Text>
      </View>
      <ScrollView ref={rolagem} contentContainerStyle={s.conteudo}>
        <View style={s.aviso}>
          <Text style={s.avisoTexto}><Text style={s.negrito}>Protótipo acadêmico, sem validade diagnóstica.</Text> O resultado não substitui a avaliação de um médico.</Text>
        </View>

        <View style={s.cartao}>
          <Text style={s.h2}>1. Envie uma radiografia de tórax</Text>
          <Pressable style={s.botao} onPress={escolherDaGaleria} disabled={carregando} accessibilityRole="button">
            <Text style={s.botaoTexto}>Escolher imagem</Text>
          </Pressable>
          {info && info.exemplos.length > 0 && (
            <>
              <Text style={s.sub}>Ou toque em uma imagem de exemplo (dados públicos do NIH, não usados no treino):</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                {info.exemplos.map((nome, i) => (
                  <Pressable key={nome} onPress={() => analisarExemplo(nome)} disabled={carregando} style={s.miniatura} accessibilityLabel={`Analisar exemplo ${i + 1}`}>
                    <Image source={{ uri: `${api}/static/exemplos/${nome}` }} style={s.miniaturaImg} />
                    <Text style={s.miniaturaTexto}>Exemplo {i + 1}</Text>
                  </Pressable>
                ))}
              </ScrollView>
            </>
          )}
        </View>

        {erro && <View style={[s.cartao, s.erroCaixa]}><Text style={s.erroTexto}>{erro}</Text></View>}

        {(imagem || carregando) && (
          <View
            style={[s.cartao, { borderLeftWidth: 8, borderLeftColor: cor }]}
            onLayout={(e) => { yResultado.current = e.nativeEvent.layout.y; if (rolarPendente.current) rolarParaResultado(); }}
          >
            <Text style={s.h2}>2. Resultado</Text>
            {imagem && <Image source={{ uri: imagem }} style={s.rx} resizeMode="contain" />}
            {carregando && (
              <View style={s.carregando}>
                <ActivityIndicator size="large" color={CORES.azul} />
                <Text style={s.sub}>Analisando a imagem...</Text>
              </View>
            )}
            {resultado && info && (
              <View>
                <Text style={[s.rotulo, { color: cor }]}>{resultado.titulo}</Text>
                <Text style={s.linha}>Categoria detectada: <Text style={s.negrito}>{resultado.classe}</Text></Text>
                <Text style={s.linha}>Probabilidade de cardiomegalia: <Text style={s.negrito}>{resultado.percentual ?? Math.round(resultado.probabilidade * 100)}%</Text></Text>
                <View style={s.barra}>
                  <View style={[s.preenchimento, { width: `${resultado.probabilidade * 100}%` }]} />
                  <View style={[s.marca, { left: `${info.limiar_sensivel * 100}%` }]} />
                  <View style={[s.marca, { left: `${info.limiar_padrao * 100}%` }]} />
                </View>
                <Text style={s.legenda}>Abaixo de {pct(info.limiar_sensivel)}: sem achado. De {pct(info.limiar_sensivel)} a {pct(info.limiar_padrao)}: inconclusivo. A partir de {pct(info.limiar_padrao)}: sugestivo de cardiomegalia.</Text>
                <Text style={s.explicacao}>{resultado.explicacao}</Text>
                <Text style={s.sub}>Modelo: {resultado.modelo}</Text>
              </View>
            )}
          </View>
        )}

        {info && (
          <View style={s.cartao}>
            <Text style={s.h2}>Como interpretar</Text>
            <Text style={s.item}>O modelo avalia apenas cardiomegalia (coração aumentado). Outras alterações não são analisadas.</Text>
            <Text style={s.item}>No conjunto de teste ({info.metricas.n_teste} imagens), de cada 100 casos reais o modelo identificou {Math.round(info.metricas.recall * 100)}, e de cada 100 alertas {Math.round(info.metricas.precisao * 100)} estavam corretos.</Text>
            <Text style={s.item}>O desempenho não está validado para menores de 18 anos.</Text>
          </View>
        )}

        <Pressable onPress={() => setMostrarConfig(!mostrarConfig)}><Text style={s.link}>{mostrarConfig ? 'Ocultar configuração' : 'Configurar endereço do servidor'}</Text></Pressable>
        {mostrarConfig && (
          <View style={s.cartao}>
            <Text style={s.sub}>Endereço do backend Flask</Text>
            <TextInput style={s.entrada} value={api} onChangeText={setApi} autoCapitalize="none" autoCorrect={false} keyboardType="url" />
            <Pressable style={s.botaoSecundario} onPress={() => conectar(api)}><Text style={s.botaoSecundarioTexto}>Testar conexão</Text></Pressable>
            {info && <Text style={[s.sub, { color: CORES.baixa }]}>Conectado. Modelo: {info.modelo}</Text>}
          </View>
        )}
        <Text style={s.rodape}>CardioIA Fase 4, FIAP, turma 2TIAOR. Uso exclusivamente educacional.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  tela: { flex: 1, backgroundColor: CORES.azul },
  topo: { backgroundColor: CORES.azul, paddingHorizontal: 20, paddingTop: Platform.OS === 'android' ? 44 : 14, paddingBottom: 16 },
  titulo: { color: '#fff', fontSize: 26, fontWeight: '700' },
  subtitulo: { color: '#fff', opacity: 0.9, marginTop: 2 },
  conteudo: { backgroundColor: CORES.fundo, padding: 14, paddingBottom: 40, width: '100%', maxWidth: 560, alignSelf: 'center', flexGrow: 1 },
  aviso: { backgroundColor: '#fff8e1', borderColor: '#f0d58a', borderWidth: 1, borderRadius: 8, padding: 12 },
  avisoTexto: { fontSize: 14, color: '#1c2330', lineHeight: 20 },
  negrito: { fontWeight: '700' },
  cartao: { backgroundColor: '#fff', borderColor: CORES.borda, borderWidth: 1, borderRadius: 10, padding: 16, marginTop: 14 },
  h2: { fontSize: 17, fontWeight: '700', color: CORES.azul, marginBottom: 10 },
  botao: { backgroundColor: CORES.azul, borderRadius: 8, paddingVertical: 13, alignItems: 'center' },
  botaoTexto: { color: '#fff', fontSize: 16, fontWeight: '600' },
  botaoSecundario: { borderColor: CORES.azul, borderWidth: 1, borderRadius: 8, paddingVertical: 10, alignItems: 'center', marginTop: 10 },
  botaoSecundarioTexto: { color: CORES.azul, fontWeight: '600' },
  sub: { color: CORES.cinza, fontSize: 13, marginTop: 10, marginBottom: 6 },
  miniatura: { marginRight: 10, alignItems: 'center', borderColor: CORES.borda, borderWidth: 1, borderRadius: 8, padding: 4 },
  miniaturaImg: { width: 84, height: 84, borderRadius: 4, backgroundColor: '#000' },
  miniaturaTexto: { fontSize: 12, color: CORES.cinza, marginTop: 3 },
  erroCaixa: { borderColor: CORES.alta },
  erroTexto: { color: CORES.alta, fontWeight: '600' },
  rx: { width: '100%', aspectRatio: 1, borderRadius: 8, backgroundColor: '#000' },
  carregando: { alignItems: 'center', paddingVertical: 18 },
  rotulo: { fontSize: 20, fontWeight: '700', marginTop: 14, marginBottom: 6 },
  linha: { fontSize: 16, color: '#1c2330', marginVertical: 2 },
  barra: { height: 18, backgroundColor: '#e6eaf0', borderRadius: 9, marginTop: 12, overflow: 'hidden' },
  preenchimento: { height: '100%', backgroundColor: CORES.azul },
  marca: { position: 'absolute', top: 0, bottom: 0, width: 2, backgroundColor: '#1c2330' },
  legenda: { fontSize: 12, color: CORES.cinza, marginTop: 4 },
  explicacao: { fontSize: 15, color: '#1c2330', lineHeight: 22, marginTop: 10 },
  item: { fontSize: 14, color: '#1c2330', lineHeight: 20, marginBottom: 8 },
  link: { color: CORES.azul, textAlign: 'center', marginTop: 18, textDecorationLine: 'underline' },
  entrada: { borderColor: CORES.borda, borderWidth: 1, borderRadius: 8, padding: 10, fontSize: 15 },
  rodape: { textAlign: 'center', color: CORES.cinza, fontSize: 12, marginTop: 22 },
});
