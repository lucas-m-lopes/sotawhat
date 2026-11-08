# sotawhat/taxonomy.py
"""Controlled vocabularies A–G (SDD §6.5). Keys are stable: triage tags, digest labels and, from P3,
the graph use them. Labels are pt-BR (shown to the user)."""

DOMAINS = {
    "A01": "documentação clínica", "A02": "apoio à decisão", "A03": "radiologia/imagem",
    "A04": "patologia/laboratório", "A05": "terapia intensiva/deterioração", "A06": "emergência/triagem",
    "A07": "centro cirúrgico", "A08": "oncologia", "A09": "cardiologia/sinais", "A10": "farmácia clínica",
    "A11": "enfermagem", "A12": "fluxo/leitos/capacidade", "A13": "força de trabalho/escalas",
    "A14": "ciclo de receita/glosas/autorização", "A15": "suprimentos/OPME/logística",
    "A16": "experiência/acesso do paciente", "A17": "qualidade/segurança/infecção",
    "A18": "monitoramento remoto/wearables/hospital-em-casa", "A19": "telemedicina",
    "A20": "pesquisa clínica/dados/RWE", "A21": "educação médica", "A22": "governança de IA/regulação",
    "A23": "atenção primária/crônicos",
}
PROBLEMS = {
    "B01": "sobrecarga documental/burnout", "B02": "erro/atraso diagnóstico", "B03": "deterioração não detectada",
    "B04": "segurança do paciente", "B05": "variabilidade de conduta", "B06": "ineficiência de fluxo/espera",
    "B07": "escassez de força de trabalho", "B08": "perda de receita/glosas", "B09": "custo/desperdício",
    "B10": "acesso/experiência", "B11": "fragmentação de dados/interoperabilidade",
    "B12": "privacidade/conformidade", "B13": "confiabilidade/segurança da IA", "B14": "produtividade em pesquisa",
    "B15": "competência/confiança profissional",
}
TECHNIQUES = {
    "C01": "ASR/documentação ambiente", "C02": "LLMs/RAG/Q&A clínico", "C03": "agentes/orquestração",
    "C04": "modelos de fundação multimodais", "C05": "visão computacional diagnóstica",
    "C06": "patologia computacional", "C07": "visão ambiente/vídeo", "C08": "séries temporais/sinais",
    "C09": "preditivos tabulares em EHR", "C10": "generativos de eventos médicos",
    "C11": "otimização/pesquisa operacional", "C12": "PLN de extração/codificação", "C13": "automação de processos",
    "C14": "robótica/controle", "C15": "edge/wearables", "C16": "federado/privacidade",
    "C17": "dados sintéticos/pacientes simulados", "C18": "avaliação/benchmarks/monitoramento",
    "C19": "modelos pequenos/abertos/fine-tuning local", "C20": "interoperabilidade/engenharia de dados",
    "C21": "XR/BCI",
}
EVIDENCE = {
    "D0": "ideia/opinião", "D1": "pesquisa de fronteira", "D2": "estudo revisado por pares",
    "D3": "RCT/validação externa", "D4": "autorização regulatória", "D5": "implantação comercial em escala",
    "D6": "ROI/desfecho independente",
}
STAKEHOLDERS = {
    "medico": "médico", "enfermagem": "enfermagem", "farmacia": "farmácia",
    "radiologia_patologia": "radiologia/patologia", "uti": "UTI", "ps": "pronto-socorro",
    "cc": "centro cirúrgico", "oncologia": "oncologia", "rcm_admin": "ciclo de receita/admin",
    "suprimentos": "suprimentos", "paciente": "paciente", "qualidade": "qualidade",
    "pesquisa": "pesquisa/IDOR", "educacao": "educação", "ti_governanca": "TI/governança",
    "operadora": "operadora", "regulador": "regulador",
}
BR_APPLICABILITY = {
    "F0": "irrelevante para o Brasil", "F1": "global, adaptável", "F2": "depende de regulação brasileira",
    "F3": "específico do Brasil (TISS/TUSS/RNDS/SUS/Rede D'Or)",
}
CFM_RISK = {   # Resolução CFM 2.454/2026, Anexo II
    "baixo": "agendamento, logística, chatbot informativo, sumarização interna",
    "medio": "apoio à decisão sem execução autônoma",
    "alto": "influência direta em decisão crítica ou ação automatizada",
    "nao_se_aplica": "não é uso clínico de IA",
}
AUDIENCE = {"clinico": "clínico", "gestao": "gestão", "engenharia": "engenharia",
            "motor": "o próprio motor (agentes, MCP, busca, avaliação)"}


def label(key: str) -> str:
    for table in (DOMAINS, PROBLEMS, TECHNIQUES, EVIDENCE):
        if key in table:
            return table[key]
    return key


def render(table: dict) -> str:
    return " · ".join(f"{k} {v}" for k, v in table.items())
