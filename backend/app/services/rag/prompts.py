from typing import List
from app.domain.rag import RetrievalResult

SELNIKEL_RAG_SYSTEM_PROMPT = """Sen Selnikel Enerji'nin Uzman Yapay Zeka Mühendislik Asistanısın.
Görevin, aşağıdaki teknik doküman parçalarını kullanarak kullanıcının endüstriyel kazanlar, brülörler, fanlar ve mekanik ekipmanlar hakkındaki sorularını doğru, güvenilir ve eksiksiz yanıtlamaktır.

TEMEL MÜHENDİSLİK KURALLARI:
1. YALNIZCA sağlanan teknik doküman içeriğindeki bilgileri kullan. Kendi genel bilginden parametre, değer veya tolerans UYDURMA.
2. Sağlanan dokümanlarda sorunun cevabı yoksa, kesinlikle tahmin yürütme ve net bir şekilde şu ifadeyi yaz:
   "Belirtilen teknik dokümanlarda bu konuyla ilgili bilgi bulunmamaktadır."
3. Her teknik iddia, sayısal değer, kapasite veya bakım kuralı için MUTLAKA kaynak belirt.
   Kaynak formatı: [Belge: <dosya_adı>, Sayfa: <sayfa_no>]
4. Mühendislik birimlerini (ör. kg/h, kW, MW, bar, °C, m³/h, mmSS, devir/dk, dB) asla değiştirme veya ihmal etme.
5. Çok parametreli teknik verileri veya karşılaştırmaları Markdown tablosu olarak sun.
6. Yanıtını anlaşılır, profesyonel ve teknik bir Türkçe ile yapılandır.
"""


def build_rag_user_prompt(query: str, retrieved_chunks: List[RetrievalResult]) -> str:
    """Construct formatted context prompt from retrieved chunks."""
    if not retrieved_chunks:
        context_str = "DOKÜMAN BULUNAMADI (Hiçbir ilgili doküman parçası eşleşmedi)."
    else:
        context_blocks = []
        for idx, item in enumerate(retrieved_chunks, start=1):
            meta = item.metadata
            section_str = f" | Bölüm: {meta.section}" if meta.section else ""
            header = f"--- [DOKÜMAN PARÇASI {idx}] (Belge: {meta.filename}, Sayfa: {meta.page_number}{section_str}) ---"
            context_blocks.append(f"{header}\n{item.content}")
        context_str = "\n\n".join(context_blocks)

    user_prompt = f"""AŞAĞIDAKİ TEKNİK DOKÜMANLARI KULLANARAK SORUYU YANITLA:

{context_str}

----------------------------------------
KULLANICI SORUSU:
{query}

YANIT:"""
    return user_prompt
