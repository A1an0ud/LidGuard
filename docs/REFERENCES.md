# LidGuard references

Sources reviewed on **14 November 2026**. These references support the problem context, engineering setup and limitations. They do not establish the clinical performance of this prototype.

## R1

**Raspberry Pi. Getting started.** Official guidance for boot media, operating-system setup, power and peripherals.

https://www.raspberrypi.com/documentation/computers/getting-started.html

Reference for OS installation, power requirements, and initial hardware setup.

## R2

**Raspberry Pi. Camera Module software and installation.** Official CSI installation and modern `rpicam-*` application documentation.

https://www.raspberrypi.com/documentation/accessories/camera-software.html

Used for powering down before connecting CSI, identifying the Pi 4 CAMERA connector and testing capture. A third-party camera may require manufacturer-specific configuration. The old `raspistill` and original Picamera stack are not the target of this prototype.

## R3

**Raspberry Pi. Camera Module hardware.** Official camera hardware descriptions, including the legacy 5 MP Camera Module 1 and its standard/NoIR variants.

https://www.raspberrypi.com/documentation/accessories/camera.html

Camera resolution alone does not identify the sensor or IR-filter configuration. NIR capability requires identification and validation of the actual camera.

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

Optical safety depends on the final assembly and exposure conditions. A wavelength label or a component described as low-power does not establish safety for continuous viewing. No eye-directed IR illumination has been validated for this release.

## Dataset used by this release

**RT-BENE.** Cortacero K, Fischer T, Demiris Y. *RT-BENE: A Dataset and Baselines for Real-Time Blink Estimation in Natural Environments.* ICCV Workshops, 2019. DOI: [10.1109/ICCVW.2019.00147](https://doi.org/10.1109/ICCVW.2019.00147).

Dataset source: https://zenodo.org/records/3685316

The source specifies **CC BY-NC-SA 4.0** and excludes commercial use. The 100-image evaluation subset is identified in [the provenance manifest](../results/rgb_data_manifest.json); its original selection method is undocumented. Raw images are not redistributed. These are general eye images, not a validation dataset of ICU corneal exposure.

License text: https://creativecommons.org/licenses/by-nc-sa/4.0/

Attribution and reuse notes: [models/NOTICE.txt](../models/NOTICE.txt).

## Other data considered

**PopEYE_2022.** Gibertoni G, Borghi G, Rovati L. Dataset: https://doi.org/10.5281/zenodo.18595048. Related paper: *Vision-Based Eye Image Classification for Ophthalmic Measurement Systems.* Sensors. 2023;23(1):386. https://doi.org/10.3390/s23010386

PopEYE is not used to train or evaluate the classifier in this release. The source uses CC BY 4.0; its image categories do not establish clinical corneal-exposure grades. No performance result in this repository should be interpreted as PopEYE or NIR validation.
