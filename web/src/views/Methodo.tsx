export default function Methodo() {
  return (
    <div className="card">
      <h3>▸ Méthodologie</h3>
      <p>
        LobbyMirror agrège des <b>données publiques</b> de sources officielles et les croise pour estimer,
        en continu, quelles entreprises poussent quels textes législatifs.
        Aucune donnée n'est inventée : chaque signal pointe vers sa source.
      </p>

      <h4>Sources de données</h4>
      <table className="data">
        <thead><tr><th>Domaine</th><th>Source</th><th>Juridiction</th><th>Accès</th></tr></thead>
        <tbody>
          <tr><td>Propositions &amp; procédures législatives</td><td>Parlement européen (procédure search API)</td><td>UE</td><td className="mono small">gratuit</td></tr>
          <tr><td>Dossiers législatifs</td><td>data.assemblee-nationale.fr (open data)</td><td>FR</td><td className="mono small">gratuit</td></tr>
          <tr><td>Projets de loi</td><td>Congress.gov API v3</td><td>US</td><td className="mono small">clé gratuite</td></tr>
          <tr><td>Registre de transparence (lobbies)</td><td>Transparency Register UE</td><td>UE</td><td className="mono small">gratuit</td></tr>
          <tr><td>Répertoire des représentants d'intérêts</td><td>HATVP</td><td>FR</td><td className="mono small">gratuit</td></tr>
          <tr><td>Déclarations de lobbying (LDA)</td><td>LDA Senate / House bulk data</td><td>US</td><td className="mono small">gratuit</td></tr>
          <tr><td>Dons aux campagnes</td><td>FEC API (OpenSecrets en option payante)</td><td>US</td><td className="mono small">clé gratuite</td></tr>
          <tr><td>Cours de bourse</td><td>Yahoo Finance chart API</td><td>—</td><td className="mono small">gratuit</td></tr>
          <tr><td>Presse</td><td>GDELT 2.0 / NewsAPI</td><td>—</td><td className="mono small">gratuit / clé</td></tr>
        </tbody>
      </table>

      <h4 className="mt">Score de pression (0 → 100)</h4>
      <p>
        Pour chaque couple <i>entreprise ↔ texte</i>, quatre signaux sont croisés et pondérés :
      </p>
      <ul>
        <li><b>Presse</b> (poids fort) : co-mentions entreprise + sujet du texte dans les médias (GDELT/NewsAPI) ;</li>
        <li><b>Registre</b> : inscription au registre de lobbying de la juridiction + chevauchement entre domaines déclarés et thématique du texte ;</li>
        <li><b>Dons</b> (US uniquement) : contributions de l'entreprise/PAC aux parlementaires rapporteurs ou membres de la commission saisie ;</li>
        <li><b>Marché</b> : anomalie du cours de bourse autour des dates clés du texte (event study simplifié).</li>
      </ul>
      <p>
        Le score est une <b>estimation heuristique</b>, pas une preuve d'illégalité : il signale une
        pression probable et invite à vérifier les sources citées.
      </p>

      <h4 className="mt">Limites connues</h4>
      <ul>
        <li>La France n'a pas de données publiques de dons politiques au niveau candidat (système de financement public des partis) — le signal « dons » n'existe que pour les US.</li>
        <li>Le matching de noms entre registres est flou (alias, filiales) : des faux positifs sont possibles, la confiance est affichée.</li>
        <li>Les données AN (dossiers législatifs) sont rafraîchies par lots hebdomadaires ; le calendrier de vote est partiellement machine-lisible.</li>
      </ul>

      <h4 className="mt">Monétisation envisagée</h4>
      <ul>
        <li>Abonnement B2B : ONG, rédactions, cabinets d'avocats (alertes temps réel, API) ;</li>
        <li>Rapports premium : « Top 10 des lobbies les plus influents », études par secteur ;</li>
        <li>API de données croisées pour intégration presse / outils internes.</li>
      </ul>
    </div>
  )
}
