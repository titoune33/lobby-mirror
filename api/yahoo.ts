/**
 * Proxy Yahoo Finance (serverless Vercel) — contourne le CORS navigateur
 * pour le rafraîchissement "temps réel" des cours côté tableau de bord.
 *
 * GET /api/yahoo?symbol=TTE.PA
 * Types volontairement lâches : déployé tel quel sur Vercel (aucune dépendance).
 */
const UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'

export default async function handler(req: any, res: any) {
  const symbol = String(req.query.symbol ?? '')
  if (!symbol || !/^[A-Z0-9.\-]{1,12}$/i.test(symbol)) {
    return res.status(400).json({ error: 'paramètre symbol invalide' })
  }
  try {
    const upstream = await fetch(
      `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=1mo&interval=1d`,
      { headers: { 'User-Agent': UA } },
    )
    if (!upstream.ok) {
      return res.status(upstream.status).json({ error: `yahoo: HTTP ${upstream.status}` })
    }
    const data: any = await upstream.json()
    const result = data?.chart?.result?.[0]
    if (!result) {
      return res.status(404).json({ error: 'symbole inconnu' })
    }
    res.setHeader('Cache-Control', 'public, max-age=300, s-maxage=300')
    return res.status(200).json({
      symbol,
      price: result.meta?.regularMarketPrice ?? null,
      currency: result.meta?.currency ?? null,
      updated: Date.now(),
    })
  } catch (err) {
    return res.status(502).json({ error: String(err) })
  }
}
