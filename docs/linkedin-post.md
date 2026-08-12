# Post LinkedIn — lancement LobbyMirror

J'ai codé un truc qui me met un peu mal à l'aise. Et j'en suis fier.

Ça s'appelle LobbyMirror. Un tableau de bord qui croise en continu :

- les textes de loi en cours (Assemblée nationale, Parlement européen, Congrès US),
- les registres de lobbying officiels (HATVP, registre de transparence UE),
- la presse,
- bientôt les dons politiques américains et les cours de bourse.

Concrètement : qui pousse quoi, cette semaine ? TotalEnergies a 11 textes liés, dont la loi hydroélectricité. Bayer affiche un score de pression de 680. Chaque lien montre ses preuves : déclaration au registre, articles de presse, score sur 100.

Pourquoi « Black Mirror » ? Parce que tout ça était déjà public. Personne n'avait juste pris la peine de tout brancher ensemble. Ce matin : 1 854 textes de loi suivis, 310 inscriptions au registre matchées, 724 liens d'influence détectés. Zéro donnée inventée, chaque signal pointe vers sa source.

La v0.1 est en ligne, gratuite : https://lobby-mirror.vercel.app

Stack : Python pour la collecte (données ouvertes officielles uniquement), React + Vite pour le dashboard, déploiement Vercel, mise à jour quotidienne automatique. Code open source : https://github.com/titoune33/lobby-mirror

Journalistes, ONG, avocats, simples curieux : qu'est-ce que vous aimeriez y voir ? Les dons politiques américains (FEC) arrivent dès que j'active les clés API.

#Transparence #Lobbying #DataJournalism #OpenData #CivicTech #PublicAffairs
