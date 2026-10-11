Library link: https://sanle.ent.sirsi.net/client/en_US/default/search/results?qu=TITLE+AUTHOR
(spaces become +; the empty &te= can be dropped)
## Oct 11 — Step 6: first live Haiku runs (the "before")

Test profile (made up, no real child data):
1st grade, English level 1.0, Spanish level 3.0, likes dragons and soccer.
Model: claude-haiku-4-5. Prompt asks for 15 books, ~50/50 English/Spanish.

### Run 1
English | Pete the Cat and His Four Groovy Buttons | James Dean
English | Dragon's Fat Cat | Dav Pilkey
English | Click, Clack, Moo: Christmas on the Farm | Doreen Cronin
English | Elephant & Piggie: Today I Will Fly | Mo Willems
English | The Little Blue Truck | Alice Schertle
English | Cam Jansen and the Mystery of the Stolen Diamonds | David A. Adler
Spanish | The Dragon Who Liked Spicy Food | Pablo Albo
Spanish | El Dragón Perezoso | Kenneth Steven
Spanish | Fútbol: Un Juego de Equipo | Melanie Chrisawn
Spanish | Mi Amigo Dragón | Giles Andreae
Spanish | El Pequeño Dragón | Margaret Wise Brown
Spanish | La Liga de Fútbol de los Animales | David Melling
English | Fox in Socks | Dr. Seuss
English | Dragons Love Tacos | Adam Rubin
English | Henry and Mudge: The First Book | Cynthia Rylant

### Run 2 (same profile, completely different list)
English | Pete the Cat and His Four Groovy Buttons | James Dean
English | The Cat in the Hat | Dr. Seuss
English | Little Dragon | Carl Sommer
English | Hop on Pop | Dr. Seuss
English | Click, Clack, Moo: Christmas on the Farm | Doreen Cronin
English | Ant and Bee | Angela Banner
English | The Soccer Kick | Anthony and David Catrow
Spanish | El pequeño dragón | Giles Andreae
Spanish | El balón de oro | Luisa Villar Liébana
Spanish | Diego Gol | Jordi Sierra i Fabra
Spanish | El dragón de fuego | Rosa Montero
Spanish | Ronaldinho: La historia de un jugador extraordinario | Didi Hamann
Spanish | El dragón y el fútbol | Manuel Figueroa
English | The Dragon and the Knight | Tony Bradman
Spanish | Dragón busca casa | Ruth Spiro

### What I noticed
- English picks are mostly real. Spanish picks look mostly invented:
  real authors paired with titles they didn't write.
- Run 1 labeled "The Dragon Who Liked Spicy Food" as Spanish. It's an English title.
- Run 2 credits a Ronaldinho book to Didi Hamann, a German soccer
  player, not a kids' author. It matched "soccer" and made up the rest.
- Pete the Cat: James Dean is the illustrator. Eric Litwin is the
  author. My last-name match could reject a real book (false negative).
- Same input, different list every run. Haiku isn't deterministic.
- Split was 9/6 in run 1, not ~50/50. Spanish picks are picture books,
  not grade 3 level. Many English picks ignore dragons and soccer.
- The Spanish books are exactly where I needed help, and that's
  where the AI is weakest. This is why the catalog decides, not Claude.

Next: run --check to see which titles the library actually has,
then fix the prompt and compare.


### Run 3 — with --check --all (3/15 found, 0/6 Spanish)
no      English | Pete the Cat: I Love My White Shoes | James Dean
no      English | The Pout-Pout Fish | Debbie Diesen
no      English | Dinosaurs Love Underpants | Brian Tee
FOUND   English | Little Blue Truck | Alice Schertle   (shelf + Libby)
no      English | Dragon Loves Tacos | Adam Rubin
no      English | Click, Clack, Moo: Christmas on the Farm | Doreen Cronin
no      Spanish | Dragón enamorado | John Cena (translated work adapted for Spanish)
no      Spanish | El dragón de fuego | María Puncel
no      Spanish | El pequeño dragón rojo | Alf Proysen
no      Spanish | ¡Gol! Cuento de fútbol | Marta Francés
no      Spanish | Futbolito | Giordano Bruno
no      Spanish | Las aventuras de Dragón y Gato | Jaume Copons
no      English | Brown Bear, Brown Bear, What Do You See? | Bill Martin Jr.
FOUND   English | Where the Wild Things Are | Maurice Sendak   (shelf + Libby)
FOUND   English | Clifford the Big Red Dog | Norman Bridwell   (shelf + Libby)

### Two kinds of "no"
Invented by Haiku (correct no):
- "Dinosaurs Love Underpants" by Brian Tee (real book, wrong author: Claire Freedman)
- "Dragón enamorado" by John Cena, with junk text in the author field
- "Futbolito" by Giordano Bruno, a 16th-century philosopher
- Spanish titles pairing real authors with made-up books
- "Dragon Loves Tacos": Haiku dropped the "s". The library has
  "Dragons Love Tacos". Correct rejection, the title is wrong.

My code's fault (false negative):
- Brown Bear, Brown Bear. I checked the catalog myself: the library has it.
  Catalog author: "Martin, Bill, 1916-2004." Haiku said "Bill Martin Jr."
  Likely bug: the author parser takes "Jr." as the last name.
  Screenshot saved.
- Top Brown Bear results are "Audio disc" (CD + book), not Books.
  Code needs to find the print copy further down.

### Why Haiku makes things up
- Smallest model, so it has memorized less.
- Spanish kids' books are rare in its training data. It's weakest
  exactly where I need help.
- My prompt asks for 15 with every field required, so it fills
  gaps instead of saying "I only know 4."
- It can't look anything up.

Design rule: the AI recommends, the library decides.

### Ideas for later
- The catalog has Language and Lexile filters (in the sidebar), but the
  RSS feed doesn't show them. Could search the catalog first for
  Spanish books, then have Haiku pick from that real list (grounding).
- Prompt fixes to try: allow fewer than 15, "only books you're sure
  exist", prefer well-known books, dragons OR soccer.
- Possible risk: ignoring subtitles after a colon could make
  "Pete the Cat: I Love My White Shoes" match any Pete the Cat book.
  Needs a test.
