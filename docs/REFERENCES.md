# LidGuard references

Sources reviewed on **14 November 2026**. These references support the problem context, engineering setup and limitations. They do not establish the clinical performance of this prototype.

## R1

**Raspberry Pi. Getting started.** Official guidance for boot media, operating-system setup, power and peripherals.

https://www.raspberrypi.com/documentation/computers/getting-started.html

Used for preparing the Raspberry Pi. The availability of a board and microSD card does not establish that the operating system has booted successfully.

## R2

**Raspberry Pi. Camera Module software and installation.** Official CSI installation and modern `rpicam-*` application documentation.

https://www.raspberrypi.com/documentation/accessories/camera-software.html

Used for powering down before connecting CSI, identifying the Pi 4 CAMERA connector and testing capture. A third-party camera may require manufacturer-specific configuration. The old `raspistill` and original Picamera stack are not the target of this prototype.

## R3

**Raspberry Pi. Camera Module hardware.** Official camera hardware descriptions, including the legacy 5 MP Camera Module 1 and its standard/NoIR variants.

https://www.raspberrypi.com/documentation/accessories/camera.html

The team's description “5 MP CSI camera” does not establish the sensor model, manufacturer or presence of an infrared filter. Confirm from the actual component before making an NIR claim.

## R4

**The Royal College of Ophthalmologists. Eye Care in the Intensive Care Unit. April 2020.**

https://www.rcophth.ac.uk/wp-content/uploads/2026/06/Eye-care-in-the-intensive-care-unit.pdf

The PDF itself is dated April 2020; the 2026 path is not its publication date. It distinguishes complete lid closure, conjunctival exposure without corneal exposure, and any corneal exposure. A binary open/closed image prediction does not establish these clinical grades. The five-second demonstration threshold is a prototype setting, not a clinical threshold taken from this guidance.

## R5

**Chen Y, He J, Wu Q, Pu S, Song C. Prevalence and risk factors of exposure keratopathy among critically ill patients: a systematic review and meta-analysis. Nursing Open. 2024;11(1):e2061.** DOI: 10.1002/nop2.2061.

https://pmc.ncbi.nlm.nih.gov/articles/PMC10721942/

The review included 23 studies with 3,519 participants and reported pooled prevalence of 34% and pooled incidence of 23%, with substantial between-study heterogeneity. These figures describe the literature, not an estimate measured by LidGuard or a fixed rate in every ICU.

## R6

**Kousha O, Kousha Z, Paddle J. Incidence, risk factors and impact of protocolised care on exposure keratopathy in critically ill adults: a two-phase prospective cohort study. Critical Care. 2018;22:5.** DOI: 10.1186/s13054-017-1925-5.

https://pmc.ncbi.nlm.nih.gov/articles/PMC5771067/

This single-centre study of 371 patients reported a reduction in the overall rate from 21% in the observational phase to 2.6% after an eye-care protocol was introduced. It supports protocolised care; it does not prove that the LidGuard monitor improves outcomes.

## R7

**Alnefaie M, Althobaiti NS, Almatrafi A, Alnafisah HA, Alqurashi M. Developing an AI-Based Model for Lagophthalmos and Bell's Phenomenon Detection in Intensive Care Unit Patients: A Gold Standard Comparison. Cureus. 2026;18(1):e101591.** DOI: 10.7759/cureus.101591.

https://pmc.ncbi.nlm.nih.gov/articles/PMC12906128/

A small study in Taif, Saudi Arabia, describing 34 participants and 68 eyes. The article has inconsistencies in the stated specificity and some patient/eye wording. Its reported model performance is not the performance of LidGuard. No image dataset from this study is included in this repository.

## R8

**Vishay Semiconductors. Eye Safety Risk Assessment of Infrared Emitting Diodes According IEC 62471. Revision 2.1, 15 November 2021.**

https://www.vishay.com/docs/81935/eyesafe.pdf

**International Commission on Non-Ionizing Radiation Protection. Infrared radiation.**

https://www.icnirp.org/en/frequencies/infrared/index.html

Optical safety depends on the final assembly and exposure conditions. A wavelength label or a component described as low-power does not establish safety for continuous viewing. The current filming workflow uses ordinary room light and does not require uncharacterised IR illumination.

## Dataset provenance

The team-provided `LidGuard_References.docx` states that the supplied image datasets contain general-population volunteer images, not ICU patient images. Source references and licenses must remain distinct from any license applied to original project code.

**PopEYE_2022.** Giovanni Gibertoni, Guido Borghi and Luigi Rovati, University of Modena and Reggio Emilia. Dataset record supplied by the team:

https://doi.org/10.5281/zenodo.18595048

The supplied provenance document identifies CC BY 4.0 and notes that partial-opening labels in its selected subset were AI-flagged and awaiting human review. Do not treat these labels as clinician-verified ground truth. Original publication:

Gibertoni G, Borghi G, Rovati L. *Vision-Based Eye Image Classification for Ophthalmic Measurement Systems.* Sensors. 2023;23(1):386. https://doi.org/10.3390/s23010386

**RT-BENE.** Cortacero K, Fischer T, Demiris Y. *RT-BENE: A Dataset and Baselines for Real-Time Blink Estimation in Natural Environments.* ICCVW 2019. https://doi.org/10.1109/ICCVW.2019.00147

Dataset: https://zenodo.org/records/3685316

The supplied subset is marked **CC BY-NC-SA 4.0**. Preserve attribution and the noncommercial/share-alike conditions applicable to the dataset. Do not describe the research dataset or derived model as cleared for commercial deployment.

License texts:

- CC BY 4.0: https://creativecommons.org/licenses/by/4.0/
- CC BY-NC-SA 4.0: https://creativecommons.org/licenses/by-nc-sa/4.0/

**MRL Eye Dataset.** The supplied provenance document reports no stated dataset license and pending permission. It is not part of the public demo bundle. Do not redistribute it based solely on its availability online.

https://mrl.cs.vsb.cz/eyedataset.html

## Competition requirements

The team's MEDATHON 2026 clarification message permits a detailed interactive digital prototype when a physical device cannot be completed, while asking teams to distinguish completed work from future development. The team's submission message requests six real prototype images and a working-demo video of 60–90 seconds, plus a code repository link. These are team-provided submission instructions, not external scientific evidence. Check the final official upload form before submitting.

