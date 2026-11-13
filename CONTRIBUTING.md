# Agentic AI Notes mein contribute kaise karo

Madad karne ke liye shukriya. Typo ho ya naya chapter, har fix agle reader ke liye in notes ko behtar banata hai.

## 📑 Is page par

- [Madad ke tarike](#-madad-ke-tarike)
- [Repository kaise kaam karti hai](#-repository-kaise-kaam-karti-hai)
- [Page likhna](#-page-likhna)
- [Likhne ka style](#-likhne-ka-style)
- [Diagrams](#-diagrams)
- [Code snippets](#-code-snippets)
- [Accuracy aur sources](#-accuracy-aur-sources)
- [Pull request kholne se pehle](#-pull-request-kholne-se-pehle)
- [Contributions ki licensing](#-contributions-ki-licensing)

## 🙌 Madad ke tarike

- **Kuch fix karo:** typo, galat fact, toota link, ya aisa code snippet jo ab nahi chalta. [fix content](.github/ISSUE_TEMPLATE/fix-content.md) issue template use karo, ya seedha pull request bhej do.
- **Topic suggest karo:** [suggest a topic](.github/ISSUE_TEMPLATE/suggest-topic.md) template use karo.
- **Explanation behtar karo:** agar koi page padh kar confuse hue, to batao kahan. Aisa feedback sona hai.
- **Translate karo:** pehle issue kholo taaki hum structure par agree kar sakein.

Chhote fixes ke liye discussion ki zaroorat nahi. Naye page ya bade rewrite ke liye pehle issue kholo.

## 🧩 Repository kaise kaam karti hai

```mermaid
flowchart LR
    R[README.md ki table of contents] --> CR[Chapter README]
    CR --> P[Pages NN.M-topic.md]
    P --> G[GLOSSARY.md]
    P --> A[assets/diagrams]
```

*README mein har chapter ki list hai. Har chapter README mein uske pages ki list hai. Pages glossary aur shared diagrams se link karte hain.*

| Path | Wahan kya rehta hai |
| --- | --- |
| `docs/NN-chapter/` | Ek chapter: ek `README.md` overview, plus har page ki ek file, `NN.M-topic-name.md` |
| `assets/diagrams/` | Haath se banaye SVG diagrams |
| `README.md`, `SUMMARY.md` | Table of contents (detailed aur flat) |
| `GLOSSARY.md`, `CHEATSHEET.md`, `ROADMAP.md` | Terms ka index, ek page ki summary aur learning paths |

**Page jodna ya move karna ho,** to har woh jagah update karo jahan woh listed hai, taaki readers use hamesha dhoondh sakein:

1. Khud page: pehli line ka breadcrumb aur footer ke previous/next links (`<!-- FOOTER -->` ke baad).
2. Uske padosi pages ke footers, jinke previous/next links ab us par point karte hain.
3. Chapter `README.md` ki page table.
4. `README.md` ki table of contents aur `SUMMARY.md` ki list.

## 📝 Page likhna

Kisi bhi existing page ko model ki tarah use karo, jaise [1.1 What is an AI agent?](docs/01-foundations/01.1-what-is-an-ai-agent.md). Har page mein yeh hona zaroori hai:

- breadcrumb (pehli line) aur footer (`<!-- FOOTER -->` ke baad);
- difficulty badge, padhne ka time aur prerequisites;
- ek **Ek line mein** summary;
- ek **📑 Is page par** list jo har `##` heading se link kare;
- kam se kam ek diagram, italic caption ke saath jo bataye ki kya notice karna hai;
- ek worked example, key takeaways, collapsible answers wali exercises, aur aage padhne ke liye links.

**Headings aur emoji:** headings mein aise emoji mat use karo jinme invisible variation selector (U+FE0F) hota hai, jaise ⚠️ ya 🖼️. Kuch Markdown renderers yeh character anchor mein rakhte hain aur kuch hata dete hain. Isliye "Is page par" wale links kisi ek par toot jaate hain.

**Glossary:** kisi page par glossary term pehli baar aaye, to use link karo: `[tool](../../GLOSSARY.md#tool)`. Naye terms [GLOSSARY.md](GLOSSARY.md) mein alphabetical order mein jodo, har ek us page se link kare jo use samjhata hai.

## 💬 Likhne ka style

- **Simple bhasha.** Chhote sentences. Active voice. "Agent tool call karta hai", na ki "Tool agent dwara call kiya jaata hai".
- **Use karne se pehle define karo.** Jab tak koi jargon samjhaya na jaye, use mat use karo.
- **Pehle concrete.** Kisi story ya scenario se shuru karo, phir general baat karo.
- **Opinions ko mark karo.** "Practice mein hum recommend karte hain…" theek hai. Opinion ko fact ki tarah pesh karna theek nahi.
- **Vendor-neutral.** Jahan providers alag hain, kam se kam do dikhao.
- **Sirf relative links**, taaki woh GitHub par bhi chalein aur clone mein bhi.

## 🎨 Diagrams

1. **Mermaid** ko prefer karo (`flowchart`, `sequenceDiagram`, `stateDiagram-v2`). GitHub ise render karta hai.
2. Overview graphics jo Mermaid achhe se nahi bana sakta, unke liye `assets/diagrams/` mein **SVG** use karo. [diagram style guide](assets/diagrams/README.md) follow karo.
3. Har image ko **alt text** aur neeche ek **italic caption** chahiye.
4. **Sirf original kaam.** Jin images ke rights tumhare paas nahi, unhe kabhi copy ya hot-link mat karo.

## 🐍 Code snippets

- Python 3.11+, jahan madad mile wahan type hints, chhota aur padhne mein aasan.
- Har snippet **ek idea** dikhaye. Use self-contained rakho: aisi files se imports nahi jo page par nahi hain.
- Providers ko unke official SDKs se call karo. Jahan providers alag hain, dono dikhao (Anthropic aur OpenAI).
- Snippet mein kabhi asli keys mat daalo. Unhe environment se padho.
- Jab versions matter karein to pin karo. Framework pages par likha hota hai `> Last verified: <month year> with <package>==<version>`.
- Submit karne se pehle apna snippet chala ke dekho, aur pull request mein batao kaun se versions use kiye.

## 🔎 Accuracy aur sources

- Facts, benchmark numbers, paper titles ya API parameters **khud se mat banao**. Pakka nahi pata, to official source check karo ya chhod do.
- **Original sources** cite karo: official documentation, original papers, aur jaane-maane engineering posts.
- APIs jaldi badalti hain. SDK ya framework code likhne se pehle current official docs check karo.

## ✅ Pull request kholne se pehle

- Tumhara joda har relative link aur `#anchor` sahi jagah khulta hai (apne fork par page preview karo).
- Naye pages har jagah listed hain (dekho [Repository kaise kaam karti hai](#-repository-kaise-kaam-karti-hai)).
- Code snippets tumhare bataye versions ke saath chalte hain.

Poori checklist [pull request template](.github/PULL_REQUEST_TEMPLATE.md) mein hai.

## 📜 Contributions ki licensing

Contribute karke tum maante ho ki tumhara contribution baaki repository wali terms par hi licensed hai: likhe hue content aur diagrams ke liye **CC BY 4.0** ([LICENSE](LICENSE)) aur code ke liye **MIT** ([LICENSE-CODE](LICENSE-CODE)). Sirf woh kaam contribute karo jo tumne khud likha hai ya jise is tarah license karne ka tumhe haq hai.

Hamara [Code of Conduct](CODE_OF_CONDUCT.md) follow karo.
