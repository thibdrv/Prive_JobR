# Retrieve Job

> **English**: a free desktop app that collects job offers from 17 job sites and company careers pages, keeps the ones that fit you (job type, city, experience, languages, contract, salary…) and puts them in one Excel file. Go through them in the app, add statuses and notes, see statistics. The interface is in French, English or Greek (Settings menu at the top right). Run `app.py` with Python 3.10+.

Une application qui cherche les offres d'emploi qui te correspondent sur plusieurs sites et les range dans un seul fichier Excel. Tu peux aussi les parcourir directement dans sa fenêtre : lire l'offre, noter ta candidature, voir tes statistiques. Elle est gratuite : pas de compte, pas de clé, pas d'abonnement. Elle existe en français, en anglais et en grec (menu « Réglages » en haut à droite).

Sites lus :

| Site | Ce qu'il apporte |
|---|---|
| Ergodotisi.com, CyprusJobs.com, CyprusWork.com | Offres à Chypre |
| Kariera.com.cy | Offres à Chypre (les 5 plus récentes par recherche) |
| FxCareer.eu | Offres forex et fintech, surtout à Limassol |
| EURES | Le portail emploi de l'Union européenne : offres à Chypre, souvent publiées par le service public de l'emploi |
| Workable | Toutes les entreprises qui recrutent à Chypre avec Workable (plus de 400 offres : Freedom24, Libertex, Nuvei…) |
| CareerFinders.com.cy | Cabinet de recrutement : toutes les offres des catégories choisies (Data Analysis, FinTech, Forex, Online Gaming, IT…) |
| EmeraldZebra.cy | Cabinet de recrutement fintech, tech, finance et iGaming : toutes ses offres |
| Entreprises suivies | Les pages carrières d'entreprises que tu choisis (FxPro, Wolt, Capital.com, Playtech… et celles que tu ajoutes) |
| Djinni | Postes tech : à Chypre, et surtout en télétravail ouverts à l'Europe (décoché par défaut) |
| Relocate.me | Postes avec aide à la relocalisation ; il en publie peu à Chypre |
| RemoteOK, Jobicy, Remotive, We Work Remotely | Offres en télétravail ouvertes à l'Europe ou au monde entier |
| Himalayas | Offres en télétravail ouvertes aux personnes qui vivent à Chypre (décoché par défaut) |

Djinni et Himalayas sont décochés au départ dans l'onglet Sites : ils apportent surtout des offres 100 % en télétravail, plusieurs centaines à la première recherche. Coche-les si tu en veux, et filtre-les ensuite par site ou par mode de travail dans l'onglet Résultats.

Les réglages par défaut visent un profil junior à Chypre (data, développement web, postes en français / vente / support), mais tout se change dans la fenêtre.

## Installation

**Le plus simple (Windows)** : télécharge `RetrieveJob-windows.zip` dans la page *Releases* du dépôt GitHub, décompresse-le dans un dossier à toi (par exemple `Documents\Retrieve Job`) et double-clique sur `RetrieveJob.exe`. Rien d'autre à installer. Garde le `.exe` avec son dossier `_internal` (l'application est un dossier plutôt qu'un seul fichier : elle s'ouvre ainsi bien plus vite, sans se décompresser à chaque lancement). Elle range ses résultats et ses paramètres dans ce dossier. Le programme n'est pas signé (un certificat de signature est payant), donc :
- Windows peut afficher « Windows a protégé votre ordinateur » la première fois : clique sur « Informations complémentaires » puis « Exécuter quand même ».
- Si le **Contrôle intelligent des applications** (Smart App Control) de Windows 11 est activé, il bloque le programme sans proposer de l'ouvrir. Utilise alors la version Python ci-dessous, qui n'est pas concernée.

**Le plus simple (Linux)** : télécharge `RetrieveJob-linux.tar.gz` dans la même page *Releases*, décompresse-le dans un dossier à toi, puis lance le programme depuis un terminal ouvert dans ce dossier :
```
tar xzf RetrieveJob-linux.tar.gz
./RetrieveJob/RetrieveJob
```
Rien d'autre à installer (Python et la fenêtre sont dedans). Il marche sur les Linux de 2022 et plus récents (Ubuntu 22.04, Debian 12, Fedora 36…). Selon ton gestionnaire de fichiers, un double-clic sur `RetrieveJob` peut aussi l'ouvrir. Pour la notification de fin de recherche, `notify-send` doit être installé (il l'est en général).

**Avec Python (Windows, Mac, Linux)** :

1. Installe **Python 3.10 ou plus récent** depuis [python.org](https://www.python.org/downloads/). Sous Windows, coche « Add python.exe to PATH » pendant l'installation.
   - Sous Linux (Ubuntu, Debian…), installe aussi la fenêtre et les environnements Python : `sudo apt install python3-tk python3-venv`.
2. Télécharge le projet : sur GitHub, bouton vert **Code** → **Download ZIP**, puis décompresse-le où tu veux. Ou, si tu as Git : `git clone` suivi de l'adresse du dépôt.
3. Double-clique sur **`Retrieve Job.pyw`** (Windows) : l'application s'ouvre directement, sans fenêtre noire. `app.py` marche aussi, mais Windows l'ouvre d'abord dans une console, puis l'application redémarre sans elle (Python démarre deux fois, un peu plus lent). Ou, dans un terminal ouvert dans ce dossier : `python app.py` (`python3 app.py` sur Mac et Linux). La première fois, l'application installe ce qu'il lui faut dans le dossier `.venv` (environ une minute).

Pour mettre à jour, télécharge la nouvelle version et remplace les fichiers du programme. Tes résultats (`results`), tes réglages (`settings.json`) et la liste des offres déjà vues (`.cache`) ne font pas partie du téléchargement : garde-les.

## Utilisation

L'onglet **Informations** de l'application explique simplement comment l'utiliser, et ce qu'est le **Score** : le nombre de tes compétences (onglet *Autres filtres*, champ « Compétences (Score) ») que l'offre cite dans son titre ou sa description, 1 point par compétence trouvée.

1. Règle tes paramètres dans les onglets (voir plus bas), puis clique sur le bouton vert **Lancer la recherche**. Pendant la recherche, il devient rouge : **Arrêter la recherche**.
2. La barre en bas montre l'étape en cours, le temps écoulé et le temps restant estimé (calculé à partir des recherches précédentes, puis de la vitesse de lecture des offres). Le détail s'affiche dans l'onglet **Recherche**, avec le temps mis par chaque site. Une recherche a trois étapes : chercher sur les sites, lire chaque nouvelle offre, puis vérifier que les offres déjà dans le fichier sont encore en ligne.
3. À la fin, une notification indique le nombre de nouvelles offres, et l'onglet **Résultats** les montre en jaune. Si tu es dans une autre fenêtre, le bouton de l'application clignote dans la barre des tâches. La notification n'apparaît que si les notifications sont activées dans Windows (*Paramètres → Système → Notifications*).

Une recherche prend quelques minutes ; la toute première est plus longue, car toutes les offres sont nouvelles. Les sites sont interrogés en même temps, chacun avec des pauses pour ne pas le surcharger.

### L'onglet Résultats

Toutes les offres du fichier, les nouvelles en jaune, les expirées en gris.
- Filtre par catégorie, statut, site, mode de travail (sur place, hybride, télétravail) ou contrat, cherche un mot, coche « Nouvelles seulement » ou décoche « Masquer les expirées ». Le choix « (non précisé) » montre les offres qui ne disent rien sur ce point. « Tout afficher » enlève tous les filtres.
- **La recherche lit aussi les descriptions** (case « aussi dans les descriptions », décoche-la pour ne chercher que dans le tableau) : chercher « python » trouve les offres qui demandent Python même si le titre ne le dit pas. Les mots cherchés sont surlignés dans la description.
- Devant chaque offre, **une pastille de couleur pour sa catégorie** (les mêmes couleurs que dans Excel) et **un badge pour son statut** : jaune À voir, bleu Postulé, vert Entretien, rouge Refusé, gris Pas intéressé. Le statut est aussi écrit dans sa colonne, et **la ligne entière prend une teinte pâle** : bleue pour Postulé, verte pour Entretien, rouge pour Refusé, grise pour Pas intéressé (le jaune des nouvelles offres passe avant).
- Clique sur un titre de colonne pour trier (un second clic inverse l'ordre). Trier par **Score** montre d'abord les offres qui citent le plus de tes compétences.
- Clique sur une offre pour **lire sa description** en dessous du tableau (la séparation se déplace à la souris). Pour les offres trouvées avant cette version, clique sur « Charger la description ».
- Double-clique sur une offre pour l'ouvrir dans ton navigateur.
- Sélectionne une ou plusieurs offres (Ctrl+clic ou Maj+clic) et choisis un statut dans le menu **Statut** : À voir, Postulé, Entretien, Refusé, Pas intéressé, ou « Effacer le statut ». Il est enregistré dans `jobs.xlsx`.
- **Clic droit sur une offre** : l'ouvrir, changer son statut, copier son lien, annuler, actualiser.
- `F5` actualise la liste (après avoir modifié `jobs.xlsx` dans Excel, par exemple).
- Écris une **note** (« contact : Maria », « salaire à négocier »…) puis « Enregistrer la note » ou Entrée : elle va dans la colonne Notes.
- **Annuler** (ou `Ctrl+Z` hors d'un champ de texte) reprend le dernier changement de statut ou de note, jusqu'à 20 en arrière, dans l'application et dans `jobs.xlsx`.

### L'onglet Statistiques

Il est rangé en quatre sous-onglets, chacun avec ses chiffres clés en haut, dans des cartes à bord coloré :
- **Vue d'ensemble** : offres dans le fichier, nouvelles, expirées, salaire médian ; les offres trouvées par semaine, tes candidatures par statut et les offres par catégorie.
- **Offres** : par catégorie, par site, par ville et par mode de travail (sur place, hybride, télétravail).
- **Candidatures** : candidatures envoyées, entretiens, taux de réponse, offres à voir ; tes candidatures par statut et par semaine (d'après la date du statut).
- **Salaires** : salaire médian et nombre d'offres qui donnent un salaire ; salaire médian par catégorie et par ville.

La couleur d'une barre suit sa valeur, comparée à la plus haute barre du graphique, sur un dégradé continu : anthracite et rouge pour les plus faibles, orange sable au milieu, olive, vert puis vert clair pour les plus élevées (une légende le rappelle en haut de l'onglet ; en thème sombre, le dégradé part d'un gris plus clair, car une barre anthracite ne se verrait pas). Passe la souris sur une barre pour voir sa valeur. Le taux de réponse compte les offres en « Entretien » ou « Refusé » parmi celles où tu as postulé.

Les salaires comptés sont ceux des offres qui en donnent un en euros (brut par mois ; pour une fourchette, son milieu). Chaque barre indique sur combien d'offres elle repose, par exemple « 1 850 € (12) » : une médiane sur 2 offres est une indication, pas une règle. Les quartiers sont rattachés à leur ville (Strovolos à Nicosie, Ypsonas à Limassol…). Utile pour savoir quoi demander en entretien.

### Les offres expirées

À chaque recherche, l'application vérifie que les offres déjà dans le fichier sont encore en ligne (chacune au plus tous les 3 jours). Celles que leur site a retirées, ou qui affichent « This job is no longer available », sont marquées « expirée » dans la colonne En ligne, grisées et barrées dans Excel, et masquées dans l'application. Elles ne sont pas supprimées : tu gardes la trace de tes candidatures. Cette vérification se décoche dans l'onglet Recherche.

### Le fichier `results/jobs.xlsx`

**Feuille « Offres »** : une ligne par offre, les plus récentes en haut. **Les offres trouvées par la dernière recherche sont surlignées en jaune** ; à la recherche suivante, elles perdent ce surlignage. La case Catégorie a une couleur par catégorie.

| Colonne | Contenu |
|---|---|
| Trouvée le | Date de la recherche qui l'a trouvée |
| Nouvelle | « oui » pour les offres de la dernière recherche (les jaunes), pour les filtrer dans Excel |
| Catégorie | Le type de poste (data, dev…). Pour CareerFinders et EmeraldZebra, si le titre ne correspond à aucun type, c'est leur propre catégorie (« Forex », « FinTech »…). Pour les entreprises suivies, si tu as coché « Garder aussi leurs offres… » : « Entreprises suivies » |
| Score | Le nombre de tes compétences citées dans l'offre |
| Titre, Entreprise, Ville | L'offre |
| Publiée | Date de publication, quand le site la donne |
| Expérience | Ce que l'offre demande : « 2+ ans », « junior » (d'après le titre) ou « non précisé » |
| Contrat, Mode de travail | Temps plein, stage… ; sur place, hybride, télétravail. Vide quand l'offre ne le dit pas |
| Salaire | En brut par mois (un salaire annuel est divisé par 12), quand l'offre l'indique |
| Compétences | Tes compétences trouvées dans l'offre |
| Site, Lien | D'où vient l'offre, avec un lien cliquable |
| Trouvée par | La recherche qui l'a trouvée (« data analyst »…) ou la catégorie du site |
| Statut | Pour toi. L'application ne l'écrit que quand tu choisis un statut dans sa fenêtre |
| Statut modifié le | La date à laquelle tu as choisi ce statut dans l'application |
| Notes | Pour toi, comme Statut |
| En ligne | « oui », « expirée », ou vide tant que l'offre n'a pas été vérifiée |
| Vérifiée le | La dernière fois que l'application a vérifié que l'offre est en ligne |
| Description | Le texte de l'offre, le même que dans l'application |

**Feuille « Résumé »** : le nombre d'offres par catégorie, par site et par statut (ces chiffres suivent tes changements dans Excel), par semaine, et le nombre d'offres expirées.

Le fichier est écrit dans la langue choisie (colonnes, statuts, contrats…). Si tu changes de langue, l'application relit sans problème un fichier écrit dans une autre.

- **Ferme `jobs.xlsx` dans Excel avant de lancer une recherche ou de changer un statut** : Excel bloque le fichier ouvert. L'application te le dit si c'est le cas.
- **Ne supprime pas de lignes pour te débarrasser d'une offre** : mets plutôt « Pas intéressé » dans Statut et filtre.
- **Les offres trouvées il y a plus d'un mois sont retirées automatiquement** à chaque recherche (réglable). Celles qui ont un Statut restent.
- Une offre n'est jamais ajoutée deux fois, même si tu la supprimes ou qu'elle a été retirée. La même offre publiée sur deux sites (même titre, même entreprise) n'est gardée qu'une fois. Si tu utilises aussi Job Application Agent, placé dans un dossier `job_agent` à côté de celui-ci, les offres déjà dans son suivi sont ignorées.
- Pour repartir de zéro, supprime le dossier `results` et le dossier `.cache`.

### Les sauvegardes

Avant chaque recherche, une copie de `jobs.xlsx` est rangée dans `results/backups` (par exemple `jobs_2026-11-23_09-30-00.xlsx`). Les 10 dernières sont gardées ; le nombre se règle dans l'onglet Recherche (0 = pas de copie). Dans le même cadre :
- **Sauvegarder maintenant** fait une copie tout de suite, par exemple avant de modifier le fichier à la main ;
- **Restaurer…** remet une copie à la place de `jobs.xlsx` : le fichier actuel est sauvegardé juste avant, tu peux donc revenir en arrière ;
- **Ouvrir le dossier** montre les copies.

## Les paramètres

Tout se règle dans la fenêtre et s'enregistre dans `settings.json` : bouton « Enregistrer les paramètres » en bas (il apparaît sur les onglets de réglages), `Ctrl+S`, ou au lancement d'une recherche. « Paramètres par défaut… », dans le menu Réglages, remet les réglages d'origine.

**Postes** : un type de poste = une catégorie dans les résultats.
- *Recherches* : ce qui est tapé dans la recherche de chaque site.
- *Mots du titre* : une offre va dans ce type si son titre contient un de ces mots. Une offre qui ne correspond à aucun type est écartée, car les sites renvoient beaucoup d'offres sans rapport avec la recherche. Si un titre correspond à plusieurs types, le premier gagne.

**Expérience et villes** :
- *Expérience maximum* : chaque nouvelle offre est lue ; si elle demande plus d'années (« 5+ years of experience », « τουλάχιστον 4 χρόνια »…), elle est écartée. Les titres junior, graduate, trainee, intern sont toujours gardés.
- *Exclure les titres de niveau* : senior, lead, director, head of…
- *Écarter les offres qui exigent* (grec par défaut) : une offre est écartée si elle est écrite en grec ou demande le grec (« Fluent in Greek and English »). Elle est gardée quand le grec est seulement un plus (« Greek is an advantage ») ou qu'il s'agit d'autre chose (« the Greek market »).
- *Villes* : Nicosie, Larnaca, Pyla, Dali, Limassol, avec leurs autres orthographes et leurs quartiers (Strovolos, Ypsonas…). Une offre qui indique seulement « Cyprus » est gardée.
- *Lieux exclus* : une offre qui cite aussi un de ces lieux est en fait à l'étranger (« Limassol, Dubai »). Ne s'applique pas aux entreprises suivies, dont « Limassol ; Yerevan » veut dire « l'un ou l'autre ».
- *Offres publiées depuis moins de* (31 jours) et *Retirer du fichier les offres trouvées il y a plus de* (31 jours, 0 = jamais).
- *Autres mots exclus du titre* : par défaut, les langues autres que le français, l'anglais et le grec.
- *Télétravail : zones acceptées* et *Pages lues par site et par recherche*.

**Autres filtres** :
- *Compétences (Score)* : chaque compétence citée dans l'offre ajoute 1 à son Score.
- *Mots obligatoires* : l'offre doit en contenir au moins un. *Mots interdits* : l'offre est écartée si elle en contient un (« commission only »…).
- *Entreprises exclues*.
- *Contrats acceptés* et *Modes de travail acceptés*. Une offre qui ne précise rien est toujours gardée.
- *Salaire minimum* (€ brut par mois). Une offre sans salaire indiqué est gardée.

**Sites** : coche ou décoche chaque site, et choisis les catégories lues sur CareerFinders.

**Entreprises** : les entreprises dont la page carrières est lue. Ça marche pour celles qui recrutent avec Greenhouse, Lever, Workable ou SmartRecruiters (beaucoup d'entreprises fintech, forex et gaming). Pour en ajouter une, ouvre une de ses offres sur son site : si l'adresse contient `greenhouse.io/…`, `jobs.lever.co/…`, `apply.workable.com/…` ou `jobs.smartrecruiters.com/…`, colle ce lien dans le champ en haut et clique sur **Ajouter**. **Tester** dit combien d'offres elle a à Chypre. Leurs offres passent par les mêmes filtres que les autres sites ; coche « Garder aussi leurs offres qui ne correspondent à aucun type de poste » pour recevoir tous leurs postes à Chypre (catégorie « Entreprises suivies »).

**Recherche** : notification à la fin, ouverture d'Excel à la fin, vérification des offres expirées, la recherche automatique et les sauvegardes.

**Le menu « ⚙ Réglages »**, en haut à droite, regroupe :
- **Taille du texte** : petit, normal, grand ou très grand. La fenêtre s'élargit si le texte ne tient plus.
- **Lignes du tableau** : compactes (plus d'offres à l'écran), normales ou aérées (plus lisibles).
- **Thème** : clair ou sombre.
- **Langue** : français, anglais ou grec. La fenêtre se rouvre dans la langue choisie, tes réglages sont gardés.
- **Enregistrer les paramètres** (`Ctrl+S`), **Paramètres par défaut…** et **Actualiser les résultats** (`F5`).

Si tu fermes la fenêtre après avoir modifié des paramètres sans les enregistrer, l'application te propose de les enregistrer.

## La recherche automatique

Dans l'onglet **Recherche**, choisis quand elle se lance, puis clique sur **Programmer** :
- **Tous les X jours** (de 1 à 30), par exemple tous les 2 jours ;
- ou **chaque semaine, les jours cochés**, par exemple du lundi au vendredi ;
- **à l'heure et la minute choisies**, par exemple 9:30.

La recherche se lance alors sans ouvrir la fenêtre, avec les derniers paramètres enregistrés. Une notification donne le résultat. L'ordinateur doit être allumé à cette heure-là. **Arrêter** supprime la programmation.

Sous Windows, c'est une tâche « Retrieve Job » du Planificateur de tâches ; sur Mac et Linux, une ligne de `crontab`. Ce qu'une recherche automatique a affiché est dans `.cache/last_run.log`.

## Les tests automatiques

Le dossier `tests` vérifie l'application tout seul. Lance-les depuis le dossier du projet, après avoir ouvert `app.py` une fois :

```
.venv\Scripts\python.exe -m unittest
```

En quelques secondes, ils vérifient :
- la lecture des offres : années d'expérience, langues exigées, contrat, mode de travail, salaire, compétences ;
- les règles de la recherche : villes, doublons, dates, catégories, liens, programmation ;
- le fichier Excel, dans un dossier temporaire (ton vrai fichier n'est jamais touché) : écriture, relecture en français, en anglais et en grec, statuts, notes, sauvegardes, restauration ;
- les traductions : chaque phrase de l'application a sa version anglaise et grecque. Si tu modifies une phrase française dans le code sans mettre à jour `languages/`, le test le signale et indique le fichier ;
- la fenêtre elle-même (`test_window.py`, une trentaine de secondes) : elle s'ouvre sur des offres inventées, dans un dossier temporaire, passe par chaque onglet, survole les graphiques, change de thème et de taille de texte, change un statut et une note puis les annule. Le test échoue si une erreur survient, si une étape bloque la fenêtre plus de 5 secondes, ou si un changement n'arrive pas dans `jobs.xlsx`. La fenêtre apparaît à l'écran pendant ce temps.

Pour vérifier aussi que **chaque site d'emploi répond encore et se lit correctement** (environ 1 minute 30, internet nécessaire) :

```
set RETRIEVE_JOB_ONLINE=1
.venv\Scripts\python.exe -m unittest tests.test_sites_online -v
```

Un site qui a changé sa présentation y apparaît en échec, avec son nom : c'est son fichier dans `sources` qu'il faut adapter.

Sur GitHub, `.github/workflows/tests.yml` lance les tests après chaque envoi de code, et ceux des sites chaque lundi (ou à la demande, onglet *Actions*). GitHub t'envoie un e-mail en cas d'échec. Les serveurs de GitHub peuvent être bloqués par certains sites : un échec de site vu seulement sur GitHub est à revérifier depuis ton PC.

## Organisation du code

| Fichier | Rôle |
|---|---|
| `app.py` | Ouvre la fenêtre et assemble ses onglets |
| `Retrieve Job.pyw` | Le lanceur à double-cliquer sous Windows : ouvre `app.py` sans fenêtre noire |
| `window/` | La fenêtre, un fichier par partie : `results_tab.py`, `stats_view.py`, `settings_tabs.py`, `companies_tab.py`, `search_tab.py`, `info_tab.py`, et `common.py` pour ce qu'ils partagent ; `file_worker.py` lit et écrit `jobs.xlsx` en arrière-plan, `watchdog.py` note les blocages et les erreurs |
| `retrieve_jobs.py` | La recherche : interroger les sites, lire les offres, vérifier les anciennes, écrire le fichier |
| `sources/` | Un fichier par groupe de sites |
| `experience.py` | Lecture d'une offre : expérience, langues, contrat, salaire, compétences |
| `results_file.py` | Le fichier `jobs.xlsx`, les descriptions et les sauvegardes |
| `settings.py` | Les paramètres et leurs valeurs par défaut |
| `i18n.py`, `languages/` | Les langues : `i18n.py` choisit la langue, `languages/` contient un fichier par langue (`en.py`, `el.py`). Pour en ajouter une, copie `en.py`, traduis-le et ajoute-le dans `i18n.py` : les tests signalent toute phrase oubliée |
| `desktop.py` | Ouvrir un fichier, notifications, recherche automatique |
| `tests/` | Les tests automatiques |

## Créer l'exécutable (.exe)

- **À la main** : ouvre `app.py` une fois (pour l'installation), puis lance `.venv\Scripts\python.exe build_exe.py`. L'application est prête dans `dist\RetrieveJob\` (`RetrieveJob.exe` et son dossier `_internal`, environ 34 Mo), et `dist\RetrieveJob-windows.zip` (16 Mo) est le fichier à mettre dans une *Release* GitHub. Si tu utilises l'application depuis `dist\RetrieveJob`, tes résultats et réglages y sont gardés quand tu la reconstruis ; ils ne vont jamais dans le zip.
- **Automatiquement sur GitHub** : le fichier `.github/workflows/release.yml` construit l'application pour Windows et pour Linux, chacune sur sa propre machine (un système ne peut pas fabriquer le programme d'un autre), vérifie les tests avant, et crée la Release avec `RetrieveJob-windows.zip` et `RetrieveJob-linux.tar.gz` dès que tu publies un numéro de version :
  ```
  git tag v1.0
  git push origin v1.0
  ```

## Bon à savoir

- Si la fenêtre se fige plus de 4 secondes, l'application note dans `.cache/freeze.log` la ligne de code où elle était bloquée et combien de temps cela a duré ; les erreurs de la fenêtre et de ses tâches en arrière-plan vont dans `.cache/errors.log`. Joins ces fichiers si tu signales un problème.
- Rapidité :
  - L'apparence est dessinée par Tk lui-même (thème « clam », aux couleurs de l'application, clair ou sombre, avec ses propres coches) : 3 à 5 fois plus rapide que l'ancien thème Windows 11 (sv_ttk), qui dessinait chaque bouton à partir d'images. Ouvrir ou changer d'onglet prend environ 0,05 s, redimensionner la fenêtre environ 0,1 s.
  - Au démarrage (environ 1 s), les offres viennent d'une copie rapide (`.cache/offers.json`, lue en 0,01 s au lieu de 0,5 s pour `jobs.xlsx`), utilisée tant que `jobs.xlsx` n'a pas changé ; un changement de statut fait dans l'application y est reporté tout de suite. Le module Excel (openpyxl) n'est chargé que si `jobs.xlsx` doit vraiment être lu ou écrit.
  - Changer un statut ou une note ne redessine que les lignes concernées ; l'onglet Statistiques ne redessine ses graphiques que si les offres ou l'apparence ont changé, seulement ceux du sous-onglet affiché, et une seule fois à la fin d'un redimensionnement.
  - L'onglet Informations est un seul bloc de texte.
- **Journal des lenteurs** : chaque moment où la fenêtre est bloquée plus d'une demi-seconde est noté dans `.cache/slow.log`, avec l'onglet affiché et le code en cours (ou « Tk drawing the window » quand c'est le dessin de la fenêtre), ainsi que la durée de chaque démarrage. Le fichier garde ses lignes les plus récentes (200 Ko au plus). Joins-le si l'application te semble lente.
- Changer un statut ou une note s'affiche tout de suite : `jobs.xlsx` est enregistré en arrière-plan, sans bloquer la fenêtre. Le fichier est aussi lu en arrière-plan (au démarrage, avec F5, après une recherche). En quittant, l'application attend que les derniers changements soient enregistrés.
- Les fichiers (`jobs.xlsx`, `settings.json`, les fichiers de `.cache`) sont d'abord écrits à côté, puis mis à la place de l'ancien d'un seul coup : si le PC s'éteint pendant un enregistrement, l'ancien fichier reste intact. Un `settings.json` illisible (modifié à la main, par exemple) est mis de côté dans `settings.broken.json` et l'application repart des paramètres par défaut.
- Dans toutes les langues de l'application (français, anglais, grec), une espace précède ? ! : ; (en grec, « ; » est le point d'interrogation). Elle est insécable, comme celle à l'intérieur des « » : la ponctuation ne se retrouve jamais seule en début de ligne. Un test vérifie qu'aucune phrase, dans aucune langue, ne l'oublie.
- Windows, Mac et Linux : sur Mac, les raccourcis utilisent Cmd (Cmd+S, Cmd+Z) au lieu de Ctrl, dans les menus et l'onglet Informations aussi ; sous Linux, la molette fait défiler les onglets de réglages comme ailleurs. `tests/test_platforms.py` vérifie ces deux points sur n'importe quel système.
- L'application ne s'ouvre qu'une fois : un double-clic de trop ramène la fenêtre déjà ouverte au premier plan, au lieu d'en ouvrir une seconde qui enregistrerait `jobs.xlsx` en même temps.
- Pour démarrer vite, les onglets de réglages et Statistiques ne sont construits que la première fois que tu les ouvres.
- Si un site ne répond pas, il est sauté et les autres continuent. Si un site ne renvoie plus rien alors qu'il donnait des offres avant, la fin de la recherche le signale : il a sûrement changé sa présentation, et il faudra adapter son code dans le dossier `sources`.
- Une offre dont la page n'a pas pu être lue est gardée avec « page non lue » dans Expérience.
- La lecture de l'expérience, des langues, du contrat et du salaire se base sur le texte de l'offre : elle peut se tromper sur une formulation inhabituelle.
- L'API gratuite de Remotive ne donne plus qu'une dizaine d'offres récentes, donc elle trouve rarement quelque chose. Relocate.me ne laisse lire que ses dernières offres, tous pays confondus : il en trouve peu à Chypre.
- LinkedIn, Indeed, Glassdoor, Careerjet et Jooble ne sont pas inclus : ils bloquent les programmes de ce genre.

## Utilisation responsable

Cet outil est fait pour un usage personnel : chercher ses propres offres, une ou quelques fois par jour. Il lit des pages publiques en laissant des pauses entre elles. Respecte les conditions d'utilisation des sites lus, et ne t'en sers pas pour copier leurs offres en masse ou les republier.

## Licence

MIT : voir le fichier [LICENSE](LICENSE).
