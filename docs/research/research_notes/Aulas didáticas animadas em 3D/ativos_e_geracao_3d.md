# 3D assets and AI 3D generation for didactic animations (medicine/biology and AI/computing): state as of 2026-11-09

These notes support sotawhat's planned auto-generated lessons, narrated in pt-BR, with 3D animations. Rendering would use Blender/bpy, Manim or Three.js, driven by LLM-written code. The hardware is an RTX 4060 8 GB, a Ryzen 5 5500, 32 GB RAM and Windows 11, with sotawhat itself on Python 3.12.

Conventions:
- **Access date:** every URL was accessed on 2026-11-09 unless another date is given.
- **"Third-party":** marks a review, reseller or aggregator. These are lower-confidence sources.
- **Currency:** prices are in USD unless noted.
- **Derived figures:** "$/asset" figures marked *(derived)* are my own arithmetic from the cited credit prices.

---

## Key Question 1: Which free sources give anatomically or scientifically correct models that can legally be reused in generated videos? (attribution, share-alike, commercial use; covers objectives a and b)

### Takeaway
Some lessons may later be reused commercially by a Brazilian health startup. For that case, the cleanest free sources that are also scientifically grounded are:
- the HuBMAP/HRA 3D reference organs (derived from the Visible Human data, CC BY 4.0, GLB);
- BodyParts3D, relicensed to CC BY 4.0 in February 2025 (OBJ);
- MedShapeNetCore (CC BY 4.0);
- Smithsonian 3D (CC0);
- RCSB PDB (CC0) and AlphaFold DB (CC BY 4.0);
- permissively licensed tools: 3D Slicer, TotalSegmentator's default `total` task (Apache-2.0), Mol* (MIT) and cellPACK (MIT).

The main traps:
- **Z-Anatomy** is CC BY-SA 4.0, so share-alike may carry over to derived videos, and it bundles some models with NC (non-commercial) licenses.
- **Sketchfab, Objaverse and NIH 3D** license each model separately.
- **Non-commercial without a paid or written license:** TotalSegmentator's specialty tasks, NVIDIA/MONAI weights (VISTA3D, MAISI), ChimeraX, and Allen Institute content.
- **Commercial anatomy platforms** each restrict reuse in some way. Visible Body capped free use at 5 images or 20 s of video per year. BioDigital requires its logo and no ad revenue. Complete Anatomy charges for commercial and YouTube use. BioRender's commercial rights cost $95–115/month. Primal Pictures and Nucleus give prices only on request.

### Cited Findings

#### Anatomy meshes (free)

**HuBMAP / Human Reference Atlas (HRA), CCF 3D Reference Object Library (derived from the Visible Human data)**
- The models were initially built from NLM's Visible Human male and female datasets. All 3D reference objects are released under CC BY 4.0. The organs are downloadable as GLB, and the extraction sites as GLB and FBX — [HuBMAP CCF 3D Reference Library](https://hubmapconsortium.github.io/ccf/pages/ccf-3d-reference-library.html)
- The latest release listed on that page is v1.2 (3rd HRA release, June 2022). It has 25 entries, most with male and female versions:
  - Allen brain, blood vasculature, bone marrow/pelvis, eye, fallopian tube, heart, kidney, knee;
  - large intestine, liver, lungs, lymph node, ovary, pancreas, placenta, prostate;
  - skin, small intestine, spinal cord, spleen, thymus, ureter, urinary bladder, uterus;
  - plus a combined "All Organs (United)" model.

  Required citation: Browne K., Schlehlein H., Herr II B.W., Quardokus E., Bueckle A., Börner K. (2022), *HuBMAP CCF 3D Reference Object Library* — [same page](https://hubmapconsortium.github.io/ccf/pages/ccf-3d-reference-library.html)
- The same organs are mirrored on NIH 3D. The brain model (Allen data, resized to fit the Visible Human bodies) notes a licensing update in v1.3 that moved it to CC BY 4.0 — [NIH 3D entry 20960](https://3d.nih.gov/entries/20960)

**BodyParts3D (the source of Z-Anatomy)**
- The BodyParts3D README now says: "The license for this database is specified in the Creative Commons Attribution 4.0 International". The license section was last updated 2025/02/25, and the update history lists the license change on 2025/02/27.
  - Required credit: "BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International" — [BodyParts3D README_e](https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/README_e.html)
- Data: Release 4.0 meshes (2013-06-19) in Wavefront OBJ, as 99%-reduced zips (IS-A tree 136 MB; PART-OF tree 62 MB). They come with tab-delimited tables of organ IDs and names and IS-A / PART-OF inclusion and compound-organ relations.
  - Citation: Mitsuhashi N. et al., *Nucleic Acids Res* 2008 (PMID 18835852) — [same README](https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/README_e.html)

**Z-Anatomy**
- All Z-Anatomy code and content is CC BY-SA 4.0, and derivative works must be distributed under the same license.
- The models are derived from BodyParts3D, which the repo still credits as CC BY-SA 2.1 Japan, an older label that conflicts with the CC BY 4.0 notice above. Definitions come largely from Wikipedia.
- The repo also lists other reference models under CC BY-NC-SA 4.0 and CC BY-NC 4.0 — [Z-Anatomy repo](https://github.com/Z-Anatomy/Models-of-human-anatomy)
- It is distributed as a Blender atlas/app template for Windows and macOS under CC BY-SA 4.0 — [3dart.it](https://3dart.it/en/free-3d-anatomy)

**Open Anatomy Project**
- The SPL/NAC Brain Atlas (MRI of a normal volunteer, BWH/MGH) is licensed under the "3D Slicer License, section B" — [Open Anatomy: SPL/NAC atlas](https://openanatomy.org/atlas-pages/atlas-spl-nac-brain.html)
- The Open Anatomy paper says the viewer and atlas source data are distributed under a "liberal open source license" but does not name it — [Frontiers in Neuroinformatics 2017](https://www.frontiersin.org/journals/neuroinformatics/articles/10.3389/fninf.2017.00022/pdf)
- 3D Slicer's license is BSD-style and "does not impose restrictions on the use of the software" (SPDX: 3D-Slicer-1.0) — [slicer.org commercial use](https://slicer.org/commercial-use.html); [SPDX](https://spdx.org/licenses/3D-Slicer-1.0.html)

**NIH 3D (3d.nih.gov)**
- There is no blanket license: "many entries fall under public domain or Creative Commons licenses (e.g., CC-BY), others may have more restrictive terms". Users must check each file, and NIH 3D does not enforce contributors' terms — [NIH 3D Terms](https://3d.nih.gov/terms); [NIH 3D FAQ](https://3d.nih.gov/faqs)

**Visible Human Project (raw data)**
- "As of July 2019, the NLM Data License has been replaced by Terms and Conditions". No registration is needed for FTP access and there is no yearly license renewal (page last reviewed 2023-12-26) — [NLM: Getting the data](https://www.nlm.nih.gov/research/visible/getting_data.html)

**Sketchfab (CC-licensed medical models)**
- Each downloadable model has either a Standard license or a CC license. CC requires crediting the creator, except CC0. The license under which you downloaded a model prevails even if the author changes it later — [Sketchfab Help: crediting](https://help.sketchfab.com/en/articles/16152215-crediting-users-for-3d-model-downloads)
- CC BY-NC forbids commercial use and CC BY-ND forbids alterations — [Sketchfab: intro to CC licenses](https://sketchfab.com/blogs/community/an-introduction-to-creative-commons-licenses)
- Licenses on anatomy models vary. For example, one skull is CC BY-NC-ND and one anatomical scan is CC BY — [skull practice](https://sketchfab.com/3d-models/skull-practice-7a52fa4202fc46fbb1440682947e239d); [anatomical model](https://sketchfab.com/3d-models/anatomical-model-bb530aae58164a8e9ba92ea5ca2e5e4e)
- Migration to Fab:
  - Only CC BY assets migrate. CC BY-SA, CC BY-NC and similar licenses are not migrated because Fab has no equivalent license — [Epic: Migrating assets to Fab](https://dev.epicgames.com/documentation/fab/migrating-assets-to-fab)
  - Sketchfab said free models remain downloadable "until licensing becomes completely unavailable on Sketchfab" — [Sketchfab: Announcing Fab](https://sketchfab.com/blogs/community/announcing-fab-the-next-phase-for-sketchfab)
  - A forum reply said everything will eventually become "view-only" — [Unreal forum](https://forums.unrealengine.com/t/what-will-happen-to-free-downloadable-sketchfab-assets/2039791)

**Smithsonian 3D**
- CC0 open-access assets "can be used for commercial purposes without any attribution, permission, or fee". They are available as glTF, GLB and OBJ (150k-polygon and full resolution). Caveat: "CC0 only applies to copyright" — [Smithsonian Open Access FAQ](https://dashboard.si.edu/openaccess/faq)
- A bulk mirror of about 828 TB and 9.1M files has a `3d` directory with GLB/glTF/OBJ — [Source Cooperative (Harvard LIL)](https://source.coop/harvard-lil/smithsonian-open-access)

**MedShapeNet (shapes derived from patient data)**
- 23 datasets with more than 100,000 shapes, most modeled on real patients' imaging — [arXiv 2308.16139](https://arxiv.org/abs/2308.16139)
- MedShapeNetCore on Zenodo (v10, February 2024) is "Creative Commons Attribution 4.0 International".
  - Categories: teeth, coronary arteries (ASOCA), thoracic aorta, skull/cranial implants, face, abdominal organs (FLARE), kidney (KiTS), lungs and surgical instruments.
  - Formats: `.npz` with masks, point clouds and meshes, plus STL via `python -m MedShapeNetCore search_and_download ORGAN` — [Zenodo 10623506](https://zenodo.org/records/10623506)

#### Medical imaging to mesh (tools, models, datasets)

**3D Slicer**
- Commercial use is allowed. Developers say code under the Slicer license is "okay to use in commercial projects even if you distribute them" — [Slicer forum](https://discourse.slicer.org/t/slicer-usage-in-the-closed-commercial-product/14180)
- It is "NOT approved for clinical use" — [Slicer docs: About](https://slicer.readthedocs.io/en/latest/user_guide/about.html)

**TotalSegmentator** — [GitHub](https://github.com/wasserth/TotalSegmentator)
- **Licenses:**
  - The code is Apache-2.0. The default `total` task (117 classes) is "Openly available for any usage (Apache-2.0 license)".
  - These tasks need a license: `heartchambers_highres`, `appendicular_bones(_mr)`, `tissue_types(_mr)`, `tissue_4_types`, `brain_structures`, `face(_mr)`, `thigh_shoulder_muscles(_mr)`, `coronary_arteries(_LEGACY)` and `aortic_sinuses`. The body-stats and aorta-report commands are also licensed.
  - Licenses are free for non-commercial use (backend.totalsegmentator.com/license-academic). Commercial use goes through jakob.wasserthal@usb.ch.
  - `brain_aneurysm` is CC BY-NC 4.0 and "no commercial license is available".
- **Outputs:**
  - NIfTI (one file per class, or multi-label with `--ml`), DICOM SEG and RTSTRUCT.
  - Statistics and radiomics JSON, plus a preview PNG.
  - The README does not mention STL or mesh export.
- **Version:** at least 2.12 is implied, since `coronary_arteries_LEGACY` was "used until v2.12.0". The Docker example pins 2.11.0. This is an inference from the README.
- **Training data:**
  - CT v1: 1,204 CTs and 104 structures — [Zenodo 6802614](https://zenodo.org/record/6802614)
  - CT v2: 1,228 CTs and 117 structures (Zenodo 8367088), listed as CC BY 4.0 in mirror metadata — [Academic Torrents](https://academictorrents.com/details/1dfeb3186514b40a2c212c21d494c665766bfbf4)
  - MR dataset: 616 subjects; the README gives no license.

**MONAI and NVIDIA models**
- MONAI is open source under Apache 2.0 — [MONAI](https://project-monai.github.io/)
- The Model Zoo repo is Apache-2.0, but weights vary by bundle — [Model Zoo](https://github.com/project-monai/model-zoo)
- MAISI (generative CT bundle): code is Apache 2.0 and weights are under "NCLS v1" — [NGC MAISI](https://catalog.ngc.nvidia.com/orgs/nvidia/teams/monaitoolkit/models/monai_maisi_ct_generative)
- VISTA3D:
  - Weights in MONAI's Hugging Face port are under "NCLS v1" — [MONAI/VISTA3D-HF](https://huggingface.co/MONAI/VISTA3D-HF)
  - The NVIDIA NIM version is under the "NVIDIA software and model evaluation license", "for research purposes and not for clinical usage" — [NIM model details](https://docs.nvidia.com/nim/medical/vista3d/model-details.md); [build.nvidia.com card](https://build.nvidia.com/nvidia/vista-3d/modelcard)
- NV-Segment-CTMR is described as a non-commercial model — [NV-Segment-CT card](https://huggingface.co/nvidia/NV-Segment-CT/blob/main/README.md)

**Public datasets**
- Medical Segmentation Decathlon: CC BY-SA 4.0 — [AWS Open Data Registry](https://registry.opendata.aws/msd/)
- AMOS: CC BY 4.0; LIDC-IDRI (TCIA): CC BY 3.0. Both come from a secondary table in a benchmark paper — [M3DA paper, arXiv 2502.17029](https://arxiv.org/pdf/2502.17029)

#### Molecular and cellular

**RCSB PDB and AlphaFold DB**
- PDB archive files, including data from the RCSB APIs, are CC0 1.0. Molecule of the Month illustrations are CC BY 4.0. Attribution is encouraged but not required — [RCSB Policies](https://rcsb.org/pages/policies)
- AlphaFold DB data is "available for academic and commercial use, under a CC-BY-4.0 license", subject to EMBL-EBI terms — [AlphaFold DB license/disclaimer](https://alphafold.ebi.ac.uk/assets/License-Disclaimer.pdf)

**Molecular Nodes (Blender add-on)**
- **License:** the GitHub repo lists GPL-3.0, but the PyPI page's badge says MIT. The two conflict — [GitHub](https://github.com/BradyAJohnston/MolecularNodes); [PyPI](https://pypi.org/project/molecularnodes/)
- **Versions:** version numbers follow Blender ("`520.x` is built for Blender 5.2"). The latest PyPI release is **520.2.0 (2026-09-18)** and it requires **Python ~=3.13**. It installs with `pip install "molecularnodes[bpy]"` for use outside Blender, or from Blender ≥4.2 through "Get Extensions" — [same](https://pypi.org/project/molecularnodes/)
- **Formats:** PDB and mmCIF, MD trajectories (via MDAnalysis), EM density maps (`.map`) and tomography files (`.map`/`.star`). It is built on Geometry Nodes — [MN docs](https://bradyajohnston.github.io/MolecularNodes/)

**Mol\* (molstar)**
- MIT license; includes a headless "Node capture" package — [molstar GitHub](https://github.com/molstar/molstar)
- The browser "Export Animation" panel renders MP4 locally, including camera spin and rock — [Mol\* movie export](https://molstar.org/viewer-docs/tips/movie-export); [Images/Movies](https://molstar.org/viewer-docs/Images_Movies)
- MolViewSpec adds declarative, time-based animations (opacity and color, `rock`/`spin`). It is available as a Mol\* extension and as a standalone Python package — [MVS animations](https://molstar.org/mol-view-spec-docs/animations/); [MVS extension](https://molstar.org/viewer-docs/extensions/mvs/)

**ChimeraX**
- Free under the non-commercial license. Commercial use needs a separate written license, priced by number of users and valid for 3 years. Each site of a company needs its own license, and there are no free trials — [ChimeraX licensing](https://www.cgl.ucsf.edu/chimerax/docs/licensing.html); [Chimera/ChimeraX commercial licensing](https://www.cgl.ucsf.edu/chimera/commercial_license.html)

**PyMOL**
- The open-source code can be freely used and copied if copyright notices stay intact (`pymol-open-source` on PyPI) — [Debian LICENSE copy](https://sources.debian.org/src/pymol/2.5.0%2Bdfsg-1/LICENSE); [PyPI](https://pypi.org/project/pymol-open-source/)
- Incentive PyMOL is the commercial product from Schrödinger. Educational subscriptions are free for full-time students and educators — [PyMOL support](https://pymol.com/support)

**cellPACK / Mesoscope**
- MIT license, installable with pip. A web version runs at cellpack.allencell.org, and example recipes include a blood-plasma model — [cellPACK docs](https://mesoscope.github.io/cellpack)
- Mesoscope was the older web tool for curating recipes — [Scripps cellPACK](https://ccsb.scripps.edu/cellpack/)

**Allen Institute (Allen Cell) content**
- Use must be noncommercial unless agreed in writing; requests go to terms@alleninstitute.org. Academic publication of limited content is allowed with citation. Suggested credit: "Image credit: Allen Institute for Cell Science" — [Allen Terms of Use](https://alleninstitute.org/terms-of-use/); [Citation policy](https://alleninstitute.org/citation-policy)

#### Generic props and environments (hospital, devices, GPUs, datacenters)

**Poly Haven, Kenney and Quaternius**
- All are CC0 according to a third-party guide. Quaternius has about 79 packs and about 1,148 models in glTF/GLB/FBX — [Cinevva: asset licenses](https://app.cinevva.com/guides/game-asset-licenses); [Cinevva: free game assets 2026](https://app.cinevva.com/guides/game-assets-guide)

**BlenderKit**
- Two licenses, Royalty Free and CC0, both allowing commercial use. You may not resell the assets themselves — [BlenderKit licenses](https://www.blenderkit.com/docs/licenses/); [Licensing FAQ](https://www.blenderkit.com/docs/licenses/licensing-faq/)
- As of August 2026: over 22k free models, 36k free materials, 4k HDRIs and 1k brushes. The Free plan is $0 with 200 MiB of private storage. The "Full" plan is $9.90/month per seat (third-party report) — [CG Channel, Aug 2026](https://www.cgchannel.com/2026/08/get-60000-free-3d-assets-for-maya-godot-and-rhino-from-blendkit/)

**Objaverse and Objaverse-XL**
- Objaverse 1.0: the dataset is ODC-By. Objects carry CC BY 4.0, CC BY-NC 4.0, CC BY-NC-SA 4.0, CC BY-SA 4.0 or CC0 (about 3.5K objects), with each license in the metadata — [HF: allenai/objaverse](https://huggingface.co/datasets/allenai/objaverse)
- Objaverse-XL: the dataset is ODC-By v1.0, and "individual objects ... are licensed under different licenses" — [HF: allenai/objaverse-xl](https://huggingface.co/datasets/allenai/objaverse-xl)

#### Commercial 3D medical content (objective b)

**BioDigital Human**
- **May 2026 changes:** the paid individual tier (Personal Plus and equivalent premium plans) was retired, and the free Personal plan now covers core Anatomy & Physiology content only. Self-service trials for School and Business plans were replaced by a guided trial — [BioDigital support, May 2026](https://support.biodigital.com/hc/en-us/articles/39657133675927-May-2026-Changes-to-Individual-Plans-and-Free-Trials)
- **Image and video policy** (taken from a search snippet; the page returned HTTP 403 to automated fetch):
  - Educators may use 2D images or video captured from BioDigital in lecture materials at no extra cost if the BioDigital logo is clearly shown. Students may do the same with a "powered by BioDigital" logo.
  - Non-commercial publications are allowed only if the materials are "not sold in any form and do not support advertising revenue".
  - The commercial terms were not retrieved — [BioDigital Image and Video Use Policy](https://support.biodigital.com/hc/en-us/articles/1500001842741-BioDigital-s-Image-and-Video-Use-Policy)
- **Plans and prices:** "Publishing images & videos" is a feature of the Class and Institution plans. School and Business prices are not public — [BioDigital pricing (school)](https://pricing.biodigital.com/school.html)

**Visible Body**
- The permissions page (search snippet) granted use of "up to 5 images / 20 seconds of video per entity per year", provided the material "is not sold in any form". As of 2026-11-09 that URL redirects (301) to Cengage Group's general permissions page. That page routes requests through the Copyright Clearance Center or a form and does not mention Visible Body — [Visible Body permissions (redirects)](https://www.visiblebody.com/legal/permission-to-use-content-from-vb-products); [Cengage permissions](https://www.cengagegroup.com/permissions/)
- A library summary describes a maximum of five screenshots for educational and research materials — [Conestoga College library](https://clear.scholarsportal.info/conestoga/Visible_Body_Apps)

**Complete Anatomy (3D4Medical / Elsevier)**
- **Pricing:**
  - Annual subscription in Student, Professional and Institutional tiers, with an introductory discount on the Student license — [Elsevier support: pricing](https://www.elsevier.support/complete-anatomy/answer/how-does-pricing-work)
  - China store: Student ¥498/year (¥298 the first year), Professional ¥725/year — [Complete Anatomy CN store](https://store.completeanatomy.cn/)
  - No official US 2026 price was found. A third-party site says "from USD 59.99" — [IntuitionLabs](https://intuitionlabs.ai/software/medical-education-platforms/anatomy-visualization-software/complete-anatomy)
- **Professional license:** adds clinical-practice and classroom teaching permissions — [App Store listing](https://apps.apple.com/app/id1054948424). It also allows patient-education use — [Elsevier support](https://www.elsevier.support/complete-anatomy/answer/sharing-content-in-a-clinical-or-professional-practice)
- **Image and video policy:**
  - Institutional licensees "are free to use images and videos for presentation purposes".
  - Lectures in a commercial setting require permission through a form.
  - Handouts and LMS posts are allowed only within an institution that holds an Institutional License.
  - A search snippet of the same page says commercial products and publications, including ad-driven platforms (YouTube, TikTok, BiliBili), are "permitted ... at a fee". That text was not visible in the fetched version — [3D4Medical: use of imagery/videos](https://3d4medical.com/use-of-imagery-videos)
- **Social media:** Elsevier's personal-subscription terms prohibit posting content, "including ... screenshots", on social networks — [Elsevier T&C](https://www.elsevier.com/legal/elsevier-website-terms-and-conditions/elsevier-terms-and-conditions-for-personal-digital-subscriptions-and-e-books)

**Primal Pictures (Anatomy.tv)**
- Institutional access and licensing go through sales. Models come from "real human scan data", the portfolio includes 3D models and videos, and an embeddable viewer works with LMSs. No prices or video-reuse terms are public — [Primal, BACA 2026](https://primalpictures.com/news/experience-3d-digital-anatomy-learning-baca-2026/); [Primal portfolio PDF (Jun 2026)](https://primalpictures.com/wp-content/uploads/2026/06/Primal-Pictures-product-portfolio.pdf); [Citeline](https://www.citeline.com/en/products-services/clinical/primal-pictures)

**Nucleus Medical Media**
- Third-party figures: a library of 25,000+ illustrations and 1,000+ animations, custom videos at $5K–$60K+ each, plus library licensing. No official price list was found — [Knowlify comparison](https://knowlify.com/articles/best-medical-healthcare-animation-agencies)
- Market context: freelance stock assets with basic motion cost $1.5k–4k, and studios charge $5k–20k per minute — [Voka](https://voka.io/medical-animation-cost/)

**BioRender (2D only)**

| Tier | Price | Rights |
|---|---|---|
| Free | $0 | "No commercial use or publication" |
| Academic Individual | $35/month billed annually, or $39 monthly | "Academic publishing rights" |
| Academic Lab | $99/month for 5 seats | Academic publishing rights |
| Industry Individual | $95/month billed annually, or $115 monthly | "Rights for commercial usage" |

The pricing page lists no animation or video features and says nothing about video or YouTube use — [BioRender pricing](https://www.biorender.com/pricing)

### Inferences
- **Commercial-safe "canonical anatomy" layer: HRA organs plus BodyParts3D.** Both are CC BY 4.0, with no share-alike or NC clauses. The required attribution text can go automatically into the video credits. BodyParts3D's relicensing to CC BY 4.0 (February 2025) means its parts can now be used directly without inheriting Z-Anatomy's CC BY-SA.
- **Z-Anatomy and MSD: personal study only.** Under CC BY-SA, a video that adapts these models would probably have to be released as CC BY-SA. The same share-alike concern applies to meshes derived from MSD (CC BY-SA 4.0). Prefer the TotalSegmentator CT dataset (CC BY 4.0), AMOS or LIDC-IDRI. This is a legal interpretation and no legal source was consulted.
- **Heart and vessel detail in TotalSegmentator.** The default `total` task is commercial-safe. High-resolution heart chambers and coronary arteries need a license, which is free only for non-commercial use. Commercial cardiology lessons would need a TotalSegmentator commercial license or the HRA heart model instead.
- **Tool licenses mostly don't follow the frames.**
  - GPL Molecular Nodes and MIT Mol\* do not encumber rendered images and videos.
  - ChimeraX's non-commercial license restricts *who may use the software*, so a startup would need a commercial ChimeraX license. Molecular Nodes, Mol\* and open-source PyMOL avoid this.
- **Commercial anatomy platforms are not viable sources for auto-generated, possibly monetized videos.** Visible Body's former free allowance (5 images or 20 s of video per year) is tiny, and its terms are in flux after the Cengage redirect. BioDigital forbids ad revenue on non-commercial publications. Complete Anatomy charges for YouTube and commercial use. Primal and Nucleus are quote-based. They are useful at most as reference views for a physician's accuracy review.
- **Per-model license sources need automatic license capture at download time.** This applies to Sketchfab, Objaverse and NIH 3D. Sketchfab is a shrinking source because only CC BY migrates to Fab.
- **Patient data stays out of the pipeline.** Real patient CTs, such as from the user's hospital, should not be used for publishable assets. Public CC BY datasets avoid LGPD and consent issues. This is general knowledge, not from a cited source.

### Gaps
- **Visible Human:** the current Terms and Conditions text (attribution and commercial clauses) was not retrieved.
- **HRA releases:** releases after v1.2 (e.g., on humanatlas.io) were not checked, and the library page may be outdated.
- **Open Anatomy:** licenses of atlases other than SPL/NAC (abdominal, knee, inner ear) were not found.
- **Sketchfab:** whether free CC downloads still work in November 2026 is unconfirmed.
- **Poly Haven, Kenney, Quaternius:** CC0 status is confirmed only by a third-party guide, not by their license pages.
- **BioDigital:** commercial terms and School/Business prices were not found.
- **Visible Body:** current terms after the Cengage redirect and its prices were not found.
- **Complete Anatomy:** the US 2026 price and the commercial/YouTube fee schedule were not found.
- **Primal Pictures and Nucleus:** no public prices or terms.
- **Dataset licenses:** AMOS and LIDC-IDRI come only from a secondary table. The license of the TotalSegmentator MR dataset and the per-source licenses for the full (non-Core) MedShapeNet are unknown.
- **Anatomography:** the BodyParts3D web viewer was not checked.

---

## Key Question 2: What is the cheapest workable 3D-generation option per asset, and is local generation feasible on 8 GB VRAM? (covers objective c)

### Takeaway
**Cheapest hosted options:**
- **Tripo's pay-as-you-go API** is the cheapest workable hosted option. Top-ups start at $1, a text-to-3D mesh without texture costs $0.10, and a textured image-to-3D costs $0.20–0.30. Its Tripo H3.1 model ranks #4 by human preference (November 2026).
- **Tencent HY 3D Global** is close behind. It gives 200 free credits, charges $0.30 for Express or untextured models and $0.50 for a standard textured model at $0.02/credit, and serves v3.0/3.1 at no surcharge. Hunyuan3D 3.1 Pro ranks #5.
- **Quality leaders cost more or need a subscription.** Meshy (#2–3) requires a plan for API access. Rodin's API is only on the $96–120/month Business plan. Hi3D v3.0 (#1) costs $0.90 per model.

**Local generation on the RTX 4060 8 GB** works only with older or smaller open models, and their quality is clearly lower (Hunyuan3D 2.1 ranks #11):
- Hunyuan3D-2/2mini shapes at about 6 GB;
- texturing through offloading forks, which is slow;
- TRELLIS v1 through fp16 community forks;
- TripoSR.

The 2025–26 open state of the art (Hunyuan3D 2.1 full, TRELLIS.2, Step1X-3D, Direct3D-S2 at 1024) needs 10–29 GB. Studies of 2D generators show poor anatomical accuracy, and no image-to-3D study was found. AI generation is therefore fit for props and stylized cells, not for exact anatomy.

### Cited Findings

#### Quality ranking (human preference, image-to-3D, November 2026)
The Rapidata leaderboard on benchmark.ai uses Bradley–Terry scores rescaled to Elo. The data come from 306,800 votes over 61,380 pairwise matches on 357 fixed input images, with at least 5 responses per match. The page header says "updated 2026-10-06" while the version note says "2026-11-09", which conflict. It is not affiliated with Hugging Face's 3D Arena — [benchmark.ai image-to-3D](https://www.benchmark.ai/image-to-3d)

| # | Model (org) | Elo | Win rate |
|---|---|---|---|
| 1 | Hi3D v3.0 (Hitem3D / Math Magic) | 1366 | 71.2% |
| 2 | Meshy v7.1 | 1298 | 67.5% |
| 3 | Meshy v7 | 1287 | 66.9% |
| 4 | Tripo H3.1 (VAST) | 1261 | 65.4% |
| 5 | Hunyuan3D 3.1 Pro (Tencent) | 1144 | 58.4% |
| 6 | Seed3D 2.0 (ByteDance) | 1097 | 55.7% |
| 7 | TRELLIS.2 (Microsoft, open) | 1005 | 49.9% |
| 8 | Rodin Gen-2.5 High (Deemos) | 956 | 47.0% |
| 9 | Rodin Gen-2.5 Low | 772 | 35.9% |
| 10 | Pixal3D (Tencent ARC Lab) | 754 | 34.8% |
| 11 | Hunyuan3D 2.1 (open) | 750 | 34.6% |
| 12 | SAM 3D Objects (Meta, open) | 658 | 29.8% |

TripoSG, Step1X-3D and Direct3D-S2 are not on this leaderboard — [same](https://www.benchmark.ai/image-to-3d). The Hugging Face 3D Arena is an open platform based on pairwise human votes (paper from mid-2025) — [arXiv 2506.18787](https://arxiv.org/html/2506.18787v1)

#### Model and version facts (emphasis on Chinese models)

**Hunyuan3D (Tencent)**
- **Open-weights line:**
  - 2.0 (January 2025): shapes need 6 GB VRAM and shape plus texture needs 16 GB in total.
  - 2mini (0.6B, March 2025), plus Turbo/Fast/mv variants.
  - A Blender add-on (January 2025) connects to a local API server. A `--low_vram_mode` flag exists. Windows is supported — [GitHub Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2)
  - 2.1 (June 13, 2025) adds open PBR texturing: 10 GB for shapes, 21 GB for texture and 29 GB for both — [GitHub Hunyuan3D-2.1](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1)
- **License (Hunyuan3D 2.1 Community License):**
  - The Territory excludes "the European Union, United Kingdom and South Korea".
  - Services with over 1M monthly active users must request a license.
  - Outputs may not be used "to improve any other AI model".
  - Distributions need a NOTICE file.
  - The acceptable-use policy bans "unlicensed practice of ... medical/health" and high-stakes automated decisions in medicine — [LICENSE](https://raw.githubusercontent.com/Tencent-Hunyuan/Hunyuan3D-2.1/main/LICENSE)
- **Hosted only (third-party, tested 2026-09-08):** 2.5, PolyGen (July 2025), 3.0 (September 2025) and 3.1 (January 2026, up to 8 input views). Hunyuan3D-Omni and Hunyuan3D-Part (September 2025, a "light" open version) are open — [triposr.org versions guide](https://triposr.org/blog/hunyuan3d-versions)
- **3.0 announcement:** "1536³ geometric resolution, and 3.6B voxel ultra-HD modeling" — [Tencent Hunyuan on X](https://x.com/TencentHunyuan/status/1967873084960260470)
- **"3.5" version:** a Tencent Cloud article mentions it, but it was not confirmed elsewhere — [Tencent Cloud techpedia](https://www.tencentcloud.com/techpedia/148305?lang=en)

**TRELLIS.2 (Microsoft)**
- 4B parameters, MIT license. Needs at least 24 GB, verified on A100/H100, and tested on Linux only — [HF microsoft/TRELLIS.2-4B](https://huggingface.co/microsoft/TRELLIS.2-4B)
- Resolutions are 512³, 1024³ and 1536³, taking about 3 s, 17 s and 60 s on an H100. Output is GLB with PBR materials, and the paper is dated December 16, 2025 — [same](https://huggingface.co/microsoft/TRELLIS.2-4B)
- A Japanese CG site warns that its nvdiffrast/nvdiffrec dependencies use NVIDIA's source license, limited to research and evaluation, which may restrict commercial use. This is not confirmed by a primary NVIDIA source — [CGWORLD](https://cgworld.jp/flashnews/01-202601-TRELLIS2.html)

**Tripo (VAST)**
- The API is organised in H, P and Splat series, sold as prepaid credits at "1 credit = $0.01" ("100 credits = $1.00", top-ups "From $1"). Enterprise terms are available through business@tripo3d.ai — [Tripo API pricing](https://developers.tripo3d.ai/en/pricing)
- A search summary of Tripo's billing docs says the API will display prices in RMB from December 1, 2026 (1 credit = ¥0.07). This was not fetched and it conflicts with a USD changelog — [Tripo billing docs](https://developers.tripo3d.com/en/docs/billing); [changelog](https://developers.tripo3d.ai/en/docs/changelog)
- Its open models: UniRig (MIT, with Tsinghua) — [HF VAST-AI/UniRig](https://huggingface.co/VAST-AI/UniRig); TripoSG (1.5B, ">8GB VRAM") — [HF VAST-AI/TripoSG](https://huggingface.co/VAST-AI/TripoSG)

**Rodin / Hyper3D (Deemos)**

| Plan | Price | Output / access |
|---|---|---|
| Free | "Pay by result" | "Direct credits cost $1.5 per credit" |
| Creator | $30/month, or $24/month billed yearly | about 60 models |
| Business | $120/month, or $96/month billed yearly | about 416 models; the only self-serve plan with API (120–240 RPM) |
| Enterprise | Custom | custom API terms |

Source: [hyper3d.ai/pricing](https://hyper3d.ai/pricing). The Gen-2 API notes:
- "Base generation costs only 0.5 credits", and HighPack upgrades textures from 2K to 4K — [Rodin Gen-2 API](https://docs.hyper3d.ai/en/api-specification/rodin-gen2)
- Another version of the docs (search summary) says a Business subscription is required and HighPack adds 1 credit — [developer.hyper3d.ai Gen-2](https://developer.hyper3d.ai/api-specification/rodin-generation-gen2)

**Meshy**
- The API sells prepaid credits, and meshy-7.1 is the latest model. USD per credit is not stated on the API page — [Meshy API pricing](https://docs.meshy.ai/en/api/pricing)
- The plan page, seen from Brazil, shows prices in BRL:

  | Plan | Price | Credits/month | API | Output license |
  |---|---|---|---|---|
  | Free | R$0 | 100 | — | CC BY 4.0, "commercial use with attribution" |
  | Starter | R$54/month | 250 | — | private, commercial license |
  | Pro | R$107.9/month | 1,000 | "API & MCP" | private, commercial license |
  | Premium | R$216/month | 3,000 | marked in the comparison table | "Private & Customer owned" |
  | Studio | R$380/month | 5,500 (shared) | "API Console" | "Private & Customer owned" |

  Source: [meshy.ai/pricing](https://www.meshy.ai/pricing). The docs confirm "Free: CC BY 4.0 ... attribution required" — [Meshy web-app pricing docs](https://docs.meshy.ai/en/webapp/pricing)
- A third-party source gives Pro as "$20" a month, using different plan names — [renderahouse](https://www.renderahouse.com/blog/meshy-pricing)

**Seed3D (ByteDance)**
- Doubao-Seed3D-2.0 is available through the Volcano Engine Ark experience center and API (as of 2026-08-29). There are no downloadable weights and no published English per-generation price.
- Features: PBR materials, segmentation into functional parts with part completion, and inference of articulation (joint types, axes, ranges, URDF output). It also generates scenes — [The Rundown: Seed3D](https://www.therundown.ai/tools/seed-3d)
- A reseller charges $0.353 per generation — [Atlas Cloud](https://www.atlascloud.ai/models/seed-3d)
- Volcano Ark's rate card is in CNY and registration requires Chinese identity verification (third-party) — [TechJack](https://techjacksolutions.com/ai-tools/bytedance-seed/bytedance-seed-pricing/)

**Step1X-3D (StepFun)**
- Apache 2.0, with a 1.3B geometry model and a 3.5B texture model. The full pipeline needs **27 GB** (29 GB with the label variant) and takes 152 s for 50 steps. There is no low-VRAM mode. Released May 13, 2025, it reuses Hunyuan3D 2.0's rasterizer — [GitHub stepfun-ai/Step1X-3D](https://github.com/stepfun-ai/Step1X-3D)

**Direct3D-S2 (Nanjing University, DreamTech, Fudan, Oxford; NeurIPS 2025)**
- MIT license, weights released May 30, 2025. "512 resolution requires at least 10GB of VRAM, and 1024 ... around 24GB" — [README mirror](https://gitserver.onethingai.com/ai-models/Direct3D-S2/raw/branch/main/README.md); [arXiv 2505.17412](https://arxiv.org/abs/2505.17412v1)

**Hi3D (formerly Hitem3D, Math Magic)**
- docs.hitem3d.ai now redirects (301) to docs.hi3d.ai, which confirms the rebrand. The price is 1 credit = $0.020 — [Hi3D API pricing](https://docs.hi3d.ai/en/api/getting-started/pricing)
- Third-party plan prices: Free 100 one-time credits; Pro $19.90/month for 1,000 credits; Max $39.90 for 2,400; Ultra $129.90 for 8,000 — [Trify3D review](https://trify3d.com/blog/hi3d-ai-3d-generator-review)

**SAM 3D Objects (Meta, November 2025)**
- Released under Meta's custom "SAM License", which is royalty-free and allows commercial use according to Roboflow. Weights are gated on Hugging Face, and no official VRAM figure was found — [Roboflow: SAM 3 license](https://roboflow.com/model-licenses/segment-anything-3)

#### Price per asset through hosted APIs
"Derived" USD figures are my arithmetic from the stated credit prices.

| Vendor / model | Cheapest useful call | "Standard" textured asset | Other relevant | Source |
|---|---|---|---|---|
| **Tripo** (H/P series), $0.01/credit | Text-to-3D, no texture: 10 cr = **$0.10** | Image-to-3D: 20 cr ($0.20) without texture, **30 cr ($0.30)** with standard texture; Text-to-3D textured: 20 cr ($0.20) | HD texture +$0.10; 8K Ultra +$0.20; HD geometry +$0.20; quad mesh +$0.05; smart low-poly +$0.10 | [Tripo pricing](https://developers.tripo3d.ai/en/pricing) |
| **Tencent HY 3D Global** (Professional / Express), postpaid $0.02/credit; prepaid packs $0.0135–0.015/credit | Geometry (untextured) 15 cr, or Express 15 cr = **$0.30** postpaid ($0.20–0.225 prepaid, derived) | Normal 25 cr = **$0.50** postpaid ($0.34–0.375 prepaid, derived); +PBR, +multi-view or +face count adds 10 cr each | 200 free credits (1 year); v3.0/3.1 at no extra cost; failed tasks not charged; default concurrency 3 (Pro) / 1 (Express); page updated 2026-05-08 | [Tencent Cloud Global billing](https://www.tencentcloud.com/document/product/1284/75281) |
| **Tencent 混元生3D (China)**, postpaid ¥0.12/credit; packs ¥0.09–0.10/credit | Geometry 15 cr; 极速版 (Rapid) 15 cr ≈ ¥1.35–1.8 (derived) | Normal 20 cr ≈ **¥1.8–2.4** (derived) | 100 free credits; page updated 2026-07-24 | [Tencent Cloud CN billing](https://cloud.tencent.com/document/product/1804/123461) |
| **Meshy API** | meshy-6-lite mesh-only: **5 cr** | meshy-7.1 image-to-3D: 20 cr mesh-only, **30 cr** with 2K/4K textures, 35 cr with 8K; meshy-6-lite textured 15 cr | USD/credit not on the API page; the Pro plan (R$107.9 for 1,000 cr ≈ R$0.108/cr, derived) has the API | [Meshy API pricing](https://docs.meshy.ai/en/api/pricing); [Meshy plans](https://www.meshy.ai/pricing) |
| **Hi3D** (ex-Hitem3D), $0.02/credit | v1.5 at 512: 15 cr = **$0.30** | v2.1 1536 "fast" (PBR): 25 cr = **$0.50**; v3.0 2048 "quality": 45 cr = $0.90; v3.0 2048 "master": 145 cr = $2.90 | Split (parts) 20 cr = $0.40 | [Hi3D pricing](https://docs.hi3d.ai/en/api/getting-started/pricing) |
| **Rodin Gen-2** | 0.5 credit per generation | HighPack (4K textures): +1 credit according to one doc version | API needs Business at $96–120/month; Free plan direct credits cost $1.50 | [hyper3d.ai/pricing](https://hyper3d.ai/pricing); [Gen-2 API](https://docs.hyper3d.ai/en/api-specification/rodin-gen2) |
| **Seed3D 2.0** | — | Reseller $0.353 per generation | Official CNY rate card on Volcano Ark (not retrieved) | [Atlas Cloud](https://www.atlascloud.ai/models/seed-3d) |

Free consumer quotas:
- Tencent's hosted platform gives 20 free generations per day, according to the launch press release as reported by a third party — [triposr.org](https://triposr.org/blog/hunyuan3d-versions)
- Meshy Free gives 100 credits per month in the web app, with CC BY 4.0 outputs — [Meshy docs](https://docs.meshy.ai/en/webapp/pricing)

**Tripo free-plan output rights are disputed.**
- Tripo's help page reportedly cites ToS §5.2.1, under which Tripo "retains all rights" to free users' outputs, so commercial use would need a paid plan. The page returned 403 to fetch — [Tripo help](https://www.tripo3d.ai/help/privacy-policy/how-to-use-tripo-models-commercially)
- Tripo's own blogs claim CC BY 4.0 with commercial use — [Tripo blog](https://www.tripo3d.ai/blog/commercial-use-ai-3d-models)

#### Local generation: VRAM and the RTX 4060 8 GB

| Model | License | Official VRAM | On 8 GB? | Sources |
|---|---|---|---|---|
| Hunyuan3D-2.0 / 2mini (0.6B) | Tencent Hunyuan community license; Territory excludes EU/UK/KR (third-party for 2.0) | 6 GB shape; 16 GB shape + texture | **Shapes yes.** Texture only through mmgp offloading forks ("2GP", WinPortable): claims range from ≥6 GB to "8 GB, 6 GB very slow". Modly says Mini needs ≥8 GB, and quantized GGUF in ComfyUI is reported at about 6–8 GB | [GitHub Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2); [Codersera guide](https://codersera.com/blog/set-up-hunyuan3d-2-on-windows-a-step-by-step-guide/); [WinPortable](https://awesome.ecosyste.ms/projects/github.com%2Fyanwenkun%2Fhunyuan3d-2-winportable); [Modly](https://themenonlab.blog/blog/modly-image-to-3d-local-ai) |
| Hunyuan3D-2.1 | Same (verified) | 10 / 21 / 29 GB | **No** for shape plus texture; shapes are borderline even with offload | [GitHub 2.1](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1) |
| TRELLIS v1 (image-large, 1.2B) | Not verified this session | 16 GB (third-party listings) | **Possible through community forks**: fp16 brought it from "16GB -> 8 GB"; 0lento's low-VRAM branch loads stages on demand but "can occasionally go OOM" | [0lento low-vram branch](https://github.com/0lento/TRELLIS/tree/low-vram/); [Reddit mirror](https://pol1.lr.ggtyler.dev/r/StableDiffusion/comments/1hudvty/trellis_imageto3d_i_made_it_work_with) |
| TRELLIS.2 (4B) | MIT, with the nvdiffrast caveat | ≥24 GB, Linux | **No.** 8 GB reports are anecdotal and slow | [HF card](https://huggingface.co/microsoft/TRELLIS.2-4B) |
| TripoSG (1.5B) | Not verified | ">8GB" | **Borderline**, shape only | [HF VAST-AI/TripoSG](https://huggingface.co/VAST-AI/TripoSG) |
| TripoSR | MIT (third-party) | about 6 GB minimum | **Yes**: 3–4 GB measured on an 8 GB RTX 5060, about 15–30 s per image; low quality (2024-era) | [Clore.ai guide](https://docs.clore.ai/guides/3d-generation/triposr); [HF workflow](https://huggingface.co/sharaborin/AIEXX_GENAI_IMAGE_TO_3D) |
| Step1X-3D | Apache 2.0 | 27–29 GB | **No** | [GitHub](https://github.com/stepfun-ai/Step1X-3D) |
| Direct3D-S2 | MIT | ≥10 GB at 512; about 24 GB at 1024 | **No** | [README mirror](https://gitserver.onethingai.com/ai-models/Direct3D-S2/raw/branch/main/README.md) |
| SAM 3D Objects | SAM License | Not published | Unknown | [Roboflow](https://roboflow.com/model-licenses/segment-anything-3) |

#### Part segmentation (useful for exploded or labelled animations)
- **Tripo:** "Generate Parts" +20 cr ($0.20); Segmentation 40 cr ($0.40); Part Completion 50 cr, or 30 cr for "Quick Cap"; Smart Segmentation 85 cr from an image or 55 cr from a model — [Tripo pricing](https://developers.tripo3d.ai/en/pricing)
- **Tencent HY 3D Global:** "3D Part Generation" 30 credits ($0.60 postpaid, derived) — [Tencent Global billing](https://www.tencentcloud.com/document/product/1284/75281)
- **Hi3D:** Split (character or general) 20 cr, $0.40 — [Hi3D pricing](https://docs.hi3d.ai/en/api/getting-started/pricing)
- **Meshy web app:** "Texture or Split option" +10 credits — [Meshy docs](https://docs.meshy.ai/en/webapp/pricing)
- **Seed3D 2.0:** functional parts, part completion and articulation with URDF output — [The Rundown](https://www.therundown.ai/tools/seed-3d)
- **Hunyuan3D-Part:** open "light" version (third-party) — [triposr.org](https://triposr.org/blog/hunyuan3d-versions)

#### Auto-rigging and animation
- **Tripo API:** Rig Check free; Auto Rig 25 cr ($0.25); Animation Retarget 10 cr ($0.10) per animation — [Tripo pricing](https://developers.tripo3d.ai/en/pricing)
- **Meshy API:** Rigging 5 cr; Animation 3 cr per action (up to 10 per request); Text to Motion 10 cr ("prime") or 3 cr ("swift") — [Meshy API pricing](https://docs.meshy.ai/en/api/pricing). In the web app, rigging and a free animation set cost 0 credits — [Meshy docs](https://docs.meshy.ai/en/webapp/pricing)
- **Tencent:**
  - Global: Auto Rigging 10 credits — [Tencent Global billing](https://www.tencentcloud.com/document/product/1284/75281)
  - China: 绑骨蒙皮 (rig and skin) 10, 文生动作 (text-to-motion) 10, 3D 人物生成 (3D character generation) 30 credits — [Tencent CN billing](https://cloud.tencent.com/document/product/1804/123461)
- **UniRig (Tsinghua + VAST, SIGGRAPH 2025):** MIT license, "at least 8GB VRAM" for inference — [HF VAST-AI/UniRig](https://huggingface.co/VAST-AI/UniRig). This conflicts with "~60GB VRAM for default settings" in a docs index — [Algolia docs index](https://docsearch.algolia.com/mcp/docs/repo/vast-ai-research/unirig)
- **Mixamo:**
  - Free, with royalty-free use of characters and animations in personal, commercial and non-profit projects. Not available for Enterprise or Federated IDs or to users with a China country code — [Adobe Mixamo FAQ](https://helpx.adobe.com/en/creative-cloud/faq/mixamo-faq.html)
  - The 2022 community FAQ bars redistributing raw files and ML training, and requires no attribution — [Adobe community FAQ](https://community.adobe.com/t5/mixamo-discussions/mixamo-faq-licensing-royalties-ownership-eula-and-tos/td-p/13234775)
  - A 2026 third-party view: unmaintained and humanoid T-pose rigs only — [Cinevva](https://app.cinevva.com/guides/free-character-animations-rigging)
- **HY-Motion 1.0 (Tencent, text-to-motion, 1.0B, flow matching):** needs 26 GB, or 24 GB for the 0.46B Lite version. License claims conflict: a community license that is free for commercial use except platforms over 100M MAU (CGWORLD), versus "MIT" (SourceForge) — [arXiv 2512.23464](https://arxiv.org/pdf/2512.23464v1); [CGWORLD](https://cgworld.jp/flashnews/01-202601-HY-Motion.html); [SourceForge mirror](https://sourceforge.net/mirror/hy-motion-1-0)

#### Suitability for scientific accuracy
- No study evaluating image-to-3D models for anatomical accuracy was found. The 2D evidence is consistently negative:
  - Of four text-to-image generators, only Gemini gave a satisfactory hand skeleton — [Clin Anat 2025, PubMed 40635255](https://pubmed.ncbi.nlm.nih.gov/40635255/)
  - For craniofacial anatomy, Midjourney v6 and DALL-E 3 did best, but neither met teaching standards. They were weakest on nerves, vessels, foramina and sutures — [PMC11989924](https://pmc.ncbi.nlm.nih.gov/articles/PMC11989924/)
  - DALL-E rendered 56.7% of structures as present, and 66.0% of those were correct. Accuracy was low for complex structures such as the lumbar plexus and celiac trunk — [PubMed 42478089](https://pubmed.ncbi.nlm.nih.gov/42478089/)
- A JMIR Medical Education perspective describes "hallucinations" of nonexistent structures. It proposes that an accurate 3D structure be generated first, with AI handling only style, angle and lighting — [PMC13493040](https://pmc.ncbi.nlm.nih.gov/articles/PMC13493040/)

### Inferences
- **Cheapest workable per asset:** Tripo API, with no subscription and a $1 minimum.
  - $0.10 for an untextured prop, $0.20–0.30 textured, and $0.25 more for an auto-rig.
  - It ranks #4 (Elo 1261), close to Meshy (#2–3), which effectively costs about $0.60 per textured model (30 cr at about $0.02/cr) plus a subscription.
- **Runner-up:** Tencent HY 3D Global, $0.30–0.50 per asset.
  - Its 200 free credits cover about 8 standard or about 13 Express/geometry generations.
  - v3.1 at no surcharge ranks #5.
  - The Chinese console is cheaper (about ¥1.8–2.4 per textured model), but it probably requires a mainland-China Tencent Cloud account. That account requirement was not verified in this session.
- **Quality vs. price:** Hi3D v3.0 is the quality leader at $0.90. Rodin's per-generation cost is low, but the $96–120/month Business plan required for the API makes it the worst choice at low volume.
- **Budget per lesson:** with 5–10 props per lesson, generation would cost about $1–5. Caching every generated asset in a reusable library (props recur across lessons) should drive the marginal cost toward zero.
- **Local on the RTX 4060:**
  - Feasible for "schematic" props: GPUs, server racks, hospital beds, devices.
  - Route: Hunyuan3D-2mini or 2.0 shapes (about 6 GB, Windows-supported, official Blender add-on), with materials applied procedurally in Blender instead of AI texturing.
  - TRELLIS v1 fp16 forks are a second option.
  - Expect a large quality gap: the best open model, Hunyuan3D 2.1, scores Elo 750 against 1144–1366 for hosted models.
  - The 2025–26 open state of the art does not fit in 8 GB.
- **Licensing for the startup path:**
  - Brazil is not in the Hunyuan Territory exclusions, so open Hunyuan weights are usable. However, the medical clauses in the acceptable-use policy and the ban on using outputs to train other models must be respected.
  - Meshy Free outputs (CC BY 4.0) are usable with a credit line.
  - Tripo free-plan outputs should be treated as non-commercial.
  - TRELLIS.2 needs dependency-license checks.
- **Accuracy:** use AI generation for props, stylized cells, bacteria and devices. Take organs and molecules from authoritative sources (HRA, BodyParts3D, CT-derived meshes, PDB). Any AI-generated biology still needs physician review.

### Gaps
- **Output ownership:** API output terms for Tripo and Tencent HY 3D were not retrieved.
- **Missing official prices:** Seed3D's official price; Rodin credits per Business plan; Meshy's USD per-credit price; Hi3D free credits.
- **Unverified licenses:** TRELLIS v1 and TripoSG were not verified this session.
- **VRAM and openness:** SAM 3D Objects VRAM and Pixal3D's openness are unknown.
- **Benchmarks:** no measured RTX 4060 timings were found for the local models. Leaderboard dates conflict, and no independent second benchmark was found for November 2026.
- **Accuracy evidence:** no quantitative study on image-to-3D anatomical accuracy was found.

---

## Key Question 3: How automatable are the PDB → animated molecule and CT → organ-mesh pipelines, how long do they take, and what reusable asset kit should be built? (covers objective d)

### Takeaway
Both pipelines can be scripted end to end with free, commercially usable components.

**PDB or AlphaFold ID → animated molecule**
- Route: Molecular Nodes (`mn.Molecule.fetch` → `add_style` → `Canvas.snapshot/animation`), which needs Blender 5.2 and Python 3.13, or Mol\* for the web (MP4 export, MolViewSpec).
- Setup takes seconds, and render time dominates.

**CT → organ meshes**
- Route: TotalSegmentator's `total` task (Apache-2.0, 117 classes), then surface extraction.
- Timing: about 0.5–3 minutes per CT on an RTX 3090, using about 5–6 GB of GPU memory. Slicer's plugin quotes 20–50 s on a CUDA GPU (≥7 GB recommended), versus 1–50 minutes on CPU.
- An RTX 4060 8 GB should cope, with `--fast` and `--body_seg` as fallbacks.

**The reusable kit** should be:
- procedural for AI concepts (tokens, embeddings, layers);
- CC0/CC BY libraries for anatomy, molecules and props;
- AI generation only for missing props;
- driven by a license manifest that writes video credits automatically.

### Cited Findings

#### PDB / AlphaFold to animated molecule
- Molecular Nodes headless API, quoted from the README — [GitHub MolecularNodes](https://github.com/BradyAJohnston/MolecularNodes):
  ```python
  import molecularnodes as mn
  canvas = mn.Canvas(mn.scene.Cycles(samples=32), resolution=(720, 480))
  mol = mn.Molecule.fetch("4ozs")
  mol.add_style("cartoon", material=mn.material.AmbientOcclusion())
  mol.add_style("ball_and_stick", selection="resname ARG")
  canvas.look_at(mol)
  canvas.snapshot("4ozs.png")
  ```
- MD trajectories animate with `mn.Molecule(mda.Universe(...))` followed by `canvas.animation("trajectory.mp4", frame_start=1, frame_end=50)`. "The API is experimental and may change between versions" — [same](https://github.com/BradyAJohnston/MolecularNodes)
- Version constraints: `molecularnodes` requires Python 3.13 ("the version Blender 5.2 uses"); `[bpy]` installs Blender as a module — [same](https://github.com/BradyAJohnston/MolecularNodes); [PyPI](https://pypi.org/project/molecularnodes/). Older API docs show `mn.Canvas(engine="CYCLES", resolution=(800, 800), transparent=True)` and a "python==3.11" requirement, so the API drifts between versions — [MN API: Canvas](https://bradyajohnston.github.io/MolecularNodes/api/reference/Canvas.html)
- Mol\* can export MP4 animations in the browser, and MolViewSpec builds animated scenes declaratively from Python — [Mol\* movie export](https://molstar.org/viewer-docs/tips/movie-export); [MVS animations](https://molstar.org/mol-view-spec-docs/animations/)
- Licenses: inputs are CC0 (PDB) and CC BY 4.0 (AlphaFold DB) — [RCSB](https://rcsb.org/pages/policies); [AlphaFold DB](https://alphafold.ebi.ac.uk/assets/License-Disclaimer.pdf)
- cellPACK (MIT, pip) builds cellular mesoscale packings from JSON recipes — [cellPACK docs](https://mesoscope.github.io/cellpack)

#### CT to organ meshes
- **Paper timings (v1, RTX 3090 with an i9 CPU):**
  - Small CT (512×512×280): 1 min 17 s with the 1.5 mm model, using about 6.1 GB of GPU memory; 34 s with the 3 mm model, about 5.2 GB.
  - Medium CT (512×512×458): 2 min 49 s at 1.5 mm and 53 s at 3 mm.

  Source: [TotalSegmentator paper, arXiv 2208.05868](https://arxiv.org/pdf/2208.05868)
- **README:**
  - `--fast` runs the 3 mm model, with lower runtime and memory.
  - Further memory savers: `--body_seg`, `--roi_subset`, `--force_split`, `--nr_thr_saving 1`.
  - A large CT with `-ml -f -sl -ro 1` takes about 30 s on GPU and 70 s on CPU.
  - v2 runtimes rose slightly because classes were added.

  Source: [TotalSegmentator GitHub](https://github.com/wasserth/TotalSegmentator)
- **3D Slicer extension:** with a CUDA GPU, fast mode takes 20–30 s and full resolution 40–50 s. Without a GPU, fast takes about 1 minute and full 40–50 minutes. A GPU with 7 GB or more is recommended — [SlicerTotalSegmentator](https://github.com/lassoan/SlicerTotalSegmentator)
- **Full-resolution memory:** a user estimates about 12 GB for some images at full resolution — [Slicer forum](https://discourse.slicer.org/t/totalsegmentator-results-computed-in-fast-mode-are-rough/28768)
- **No mesh export:** TotalSegmentator outputs NIfTI and DICOM SEG/RTSTRUCT only, so a separate surface-extraction step is required — [TotalSegmentator GitHub](https://github.com/wasserth/TotalSegmentator)
- **Ready-made meshes that skip segmentation:**
  - MedShapeNetCore: STL through a CLI, CC BY 4.0 — [Zenodo](https://zenodo.org/records/10623506)
  - HRA organs: GLB, CC BY 4.0 — [HuBMAP](https://hubmapconsortium.github.io/ccf/pages/ccf-3d-reference-library.html)
  - BodyParts3D: OBJ, with organ ID/name tables and IS-A/PART-OF trees, CC BY 4.0 — [README](https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/README_e.html)

#### Props and characters
- The official Hunyuan3D-2 Blender add-on connects Blender to a locally launched API server — [GitHub Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2)
- Hosted APIs expose rig and animation endpoints: Tripo, Meshy and Tencent — [Tripo](https://developers.tripo3d.ai/en/pricing); [Meshy](https://docs.meshy.ai/en/api/pricing); [Tencent Global](https://www.tencentcloud.com/document/product/1284/75281)
- Mixamo animations are royalty-free in videos — [Adobe](https://helpx.adobe.com/en/creative-cloud/faq/mixamo-faq.html)

### Inferences
**Automation level**
- **PDB → molecule:** fully automatable and deterministic. An LLM picks PDB/AlphaFold IDs (e.g., drug–target complexes for a therapy lesson) plus selections and styles. A template script then calls MN.
  - Python mismatch: sotawhat runs on Python 3.12, and MN needs 3.13. Run MN in a separate 3.13 venv with `molecularnodes[bpy]`, or through Blender 5.2 headless (`blender -b -P script.py`) called as a subprocess.
  - Setup (fetch and styling) takes seconds.
  - Rendering is an *unmeasured estimate*: EEVEE at roughly 0.2–1 s per frame, or Cycles at 32 samples and 720p at roughly 2–10 s per frame on an RTX 4060. A 10 s clip at 24 fps (240 frames) would then take about 1–4 minutes with EEVEE or about 8–40 minutes with Cycles.
  - Conformational changes need MD trajectories, or morphs between two PDB states. These are scriptable but take more care.
- **CT → organ meshes:** fully automatable. Steps:
  1. Public CT (TotalSegmentator dataset, CC BY 4.0).
  2. TotalSegmentator `total` with `--ml`.
  3. Per-label marching cubes (scikit-image/VTK), smoothing and decimation.
  4. Export as GLB, or OBJ for Blender.
  - Expected time is about 1–5 minutes per CT on the RTX 4060. This is extrapolated from 3090 numbers; the 4060 is slower and has less memory.
  - The 3 mm model (about 5.2 GB in the paper) should fit in 8 GB. Fall back to `--fast`, `--body_seg` or `--roi_subset` when a large scan runs out of memory.
  - 3D Slicer can do the same interactively. Its STL/OBJ segmentation export was not verified this session.
- **Anatomy lookups:** semi-automatable. An LLM maps the lesson's organ terms to HRA GLB files, or to BodyParts3D IDs through the IS-A/PART-OF tables, then assembles the scene. Every new organ set needs a one-time physician check of naming and selection.
- **AI-generated props:** semi-automatable. Steps: text or image prompt → Tripo/Tencent API → automatic checks (face count, watertightness, scale) → human approval once → cache. Generation is not deterministic, so asset reuse beats regeneration.
- **Bespoke biological choreography** (e.g., sepsis cascades, leukocyte extravasation): low automation. Use procedural, schematic animation with primitives and particles rather than "correct" 3D assets.

**Recommended reusable "asset kit" for the pipeline** (based on the licenses above)

| Domain | Assets | Source and license | Automation |
|---|---|---|---|
| AI: tokens, embeddings, attention, layers, backprop | Procedural primitives (cubes/instances, point clouds, attention arcs, layer grids) in Manim, Blender Geometry Nodes or Three.js | Own code, no license issues | Full: an LLM writes code from templates |
| AI hardware: GPU, server rack, datacenter aisle, cables | CC0 props (Poly Haven, Kenney, Quaternius, BlenderKit CC0/RF), or AI-generated (Tripo at $0.10–0.30 each) | CC0/RF; paid API output | Semi (one-time QA, then cached) |
| Canonical organs | HRA 24 organs (male and female) | CC BY 4.0, GLB | High |
| Fine anatomy: vessels, nerves, muscles, bones | BodyParts3D | CC BY 4.0, OBJ | High (ID tables) |
| Patient-like or pathological anatomy | TotalSegmentator on CC BY 4.0 CTs; MedShapeNetCore (kidney tumours/KiTS, coronaries, aorta, FLARE organs) | Apache-2.0 model; CC BY 4.0 data | High |
| Imaging scenes: CT slices, volume renders, segmentation overlays | Public CT (TotalSegmentator dataset, LIDC-IDRI) | CC BY 4.0 / CC BY 3.0 | High |
| Molecules: drugs, targets, antibodies | PDB/AlphaFold → Molecular Nodes or Mol\* | CC0 / CC BY 4.0; GPL/MIT tools | Full |
| Cells and organelles | cellPACK recipes plus procedural membranes; AI-generated stylized cells and bacteria | MIT; paid API output | Partial |
| Hospital environments and devices | BlenderKit free props, Poly Haven, AI-generated devices; Mixamo or UniRig/Meshy/Tripo for characters | RF/CC0; royalty-free | Semi |

- **Avoid on the startup track:** Z-Anatomy and MSD (share-alike), Allen Cell, ChimeraX, VISTA3D/MAISI weights, licensed TotalSegmentator tasks, Tripo free-plan outputs, and any Sketchfab or Objaverse NC/SA model. Keep them only in a "personal-study" build.
- **License manifest:** each asset gets JSON fields `{source, url, license, attribution_text, commercial_ok, share_alike, accessed}`. The renderer then writes end credits automatically and refuses NC/SA assets when building a "commercial-safe" lesson.
- **Cost:** molecules, CT meshes and the anatomy libraries cost $0. Props cost about $1–5 per lesson, and this falls toward $0 as the cached library grows. GPU time on the RTX 4060 is the main constraint, with Cycles renders taking minutes to tens of minutes per clip.

### Gaps
- No measured Molecular Nodes render times (EEVEE or Cycles) on an RTX 4060 were found. The figures above are estimates.
- No RTX 4060 benchmarks for TotalSegmentator were found. The README's runtime table is an image and could not be read.
- Not verified this session:
  - 3D Slicer's documentation on STL/OBJ segmentation export;
  - whether Molecular Nodes 520.x still imports cellPACK outputs;
  - which classes in the default `total` task cover the heart (detailed chambers are in the licensed task);
  - whether Manim's 3D capabilities can import GLB anatomy without Blender.
- The license of the TotalSegmentator MR dataset is unknown, as are HRA versions newer than v1.2, which may add organs.
