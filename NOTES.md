# Notes de développement

## Jour 1 : ingestion et chunking

- Corpus : 6 PDF (règlement ENIAD, 2 chapitres Agile, 3 chapitres Deep Learning), 198 chunks, médiane 455 caractères.
- Extraction : pypdf collait des mots (« Réseauxde », « ouplus »). Après comparaison sur mes PDF, je suis passée à PyMuPDF.
- Bruit : en-tête et pied de page répétés sur chaque page du règlement, numéros de diapositive collés au texte. Solution : suppression des lignes présentes sur au moins 40 % des pages et des lignes qui sont des numéros de page.
- Chunks de titres seuls (diapositives dont le contenu est une image) : filtrés sous 80 caractères.
- Limites connues : tableaux aplatis (perte du lien entre colonnes), schémas et formules en image non extraits, pas d'OCR.
- À vérifier au jour 4 : taille 800 / chevauchement 150, via le taux de réussite sur les 20 questions.
