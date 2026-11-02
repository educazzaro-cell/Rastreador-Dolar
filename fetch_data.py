"""Atualiza data.json com preços, curva DI e notícias. Rode depois do fechamento."""
import os, json, datetime as dt
import pandas as pd, requests, feedparser, yfinance as yf

TICKERS = {"DXY": "DX-Y.NYB", "US10Y": "^TNX", "VIX": "^VIX", "USDMXN": "MXN=X",
           "USDZAR": "ZAR=X", "IBOV": "^BVSP", "BRENT": "BZ=F", "SOJA": "ZS=F", "USDBRL": "BRL=X"}
QUERIES = ["dólar hoje", "Fed juros EUA", "Brasil fiscal juros Copom", "China economia minério"]


def prices():
    raw = yf.download(list(TICKERS.values()), period="2y", interval="1d",
                      auto_adjust=True, progress=False)["Close"]
    df = raw.rename(columns={v: k for k, v in TICKERS.items()})
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df


def selic():
    ini = (dt.date.today() - dt.timedelta(days=800)).strftime("%d/%m/%Y")
    r = requests.get("https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados",
                     params={"formato": "json", "dataInicial": ini}, timeout=30)
    r.raise_for_status()
    s = pd.Series({pd.to_datetime(x["data"], dayfirst=True): float(x["valor"]) for x in r.json()})
    return s.sort_index()


def build_csv():
    df = prices()
    # DIFJUROS aqui é um proxy: Selic meta menos juros de 10 anos dos EUA
    df["DIFJUROS"] = selic().reindex(df.index, method="ffill") - df["US10Y"]
    if os.path.exists("manual.csv"):  # colunas extras: CDS, MINERIO, FLUXO...
        m = pd.read_csv("manual.csv", parse_dates=["data"]).set_index("data")
        m.columns = [c.upper() for c in m.columns]
        df = df.join(m, how="left")
    df = df.ffill()
    ok = [c for c in df.columns if df[c].notna().sum() >= 100]
    df = df[ok].dropna().tail(300)
    return df.round(4).to_csv(index_label="data", date_format="%Y-%m-%d")


def curve():
    p = "curva_di.csv"  # vencimento,hoje,1d,1s,1m (preencha à mão ou com outra fonte)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else None


def classify(items):
    for it in items:
        it["impacto"], it["motivo"] = "neutro", ""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or not items:
        return items
    prompt = ("Para cada manchete, diga se o impacto provável no dólar frente ao real é "
              "'alta', 'baixa' ou 'neutro', com motivo de até 12 palavras. "
              'Responda só com JSON: [{"i":0,"impacto":"alta","motivo":"..."}]\n\n'
              + "\n".join(f"{i}. {it['titulo']}" for i, it in enumerate(items)))
    try:
        r = requests.post("https://api.anthropic.com/v1/messages",
                          headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                   "content-type": "application/json"},
                          json={"model": "claude-sonnet-5-5", "max_tokens": 1500,
                                "messages": [{"role": "user", "content": prompt}]}, timeout=60)
        r.raise_for_status()
        txt = r.json()["content"][0]["text"]
        for x in json.loads(txt[txt.find("["):txt.rfind("]") + 1]):
            if 0 <= x["i"] < len(items) and x["impacto"] in ("alta", "baixa", "neutro"):
                items[x["i"]]["impacto"] = x["impacto"]
                items[x["i"]]["motivo"] = str(x.get("motivo", ""))[:100]
    except Exception as ex:
        print("classificação falhou:", ex)
    return items


def news():
    seen, items = set(), []
    for q in QUERIES:
        url = ("https://news.google.com/rss/search?q=" + requests.utils.quote(q + " when:1d")
               + "&hl=pt-BR&gl=BR&ceid=BR:pt-419")
        for e in feedparser.parse(url).entries[:4]:
            if e.title in seen:
                continue
            seen.add(e.title)
            items.append({"titulo": e.title, "link": e.link,
                          "fonte": e.get("source", {}).get("title", "")})
    return classify(items[:14])


def main():
    out = json.load(open("data.json", encoding="utf-8")) if os.path.exists("data.json") else {}
    for k, fn in (("csv", build_csv), ("curve", curve), ("news", news)):
        try:
            v = fn()
            if v:
                out[k] = v
        except Exception as ex:  # mantém o valor anterior se uma fonte falhar
            print(f"{k} falhou:", ex)
    out["updated"] = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")
    json.dump(out, open("data.json", "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()
