# VitalPet-RD

### An AI Research & Development Assistant for Companion Animal Nutrition and Pet Products

VitalPet-RD is an open research and development assistant designed for the **companion animal nutrition and pet-product industry**, with a primary focus on dogs and cats.

It is built on top of **Qwen3-4B** and adds a domain-specific reasoning framework focused on:

* Pet nutrition
* Functional ingredients
* Nutraceutical formulation
* Veterinary-support products
* Scientific evidence evaluation
* Dose reasoning
* Safety assessment
* Palatability
* Formulation development
* Product-development feasibility
* Regulatory and claim considerations

VitalPet-RD is designed to evolve from a lightweight domain-specific AI assistant into a broader **Pet R&D Intelligence Platform** combining language models, scientific evidence, structured ingredient databases, formulation engines, and proprietary R&D data.

---

## Overview

General-purpose language models can provide useful scientific explanations, but they may also:

* Generate unsupported numerical recommendations
* Confuse human and animal evidence
* Generalize between dogs and cats
* Produce plausible but unverifiable scientific references
* Treat mechanistic evidence as clinical evidence
* Present formulation assumptions as established facts
* Confuse scientific evidence with regulatory permission

VitalPet-RD introduces a domain-specific reasoning framework intended to reduce these problems.

The core philosophy is:

> **Evidence before confidence.**

And more specifically:

> **It is better to say that sufficient canine/feline evidence is unavailable than to generate a precise-looking dose, study, citation, or guideline without adequate evidence.**

---

# Key Principles

## 1. Evidence First

Scientific claims should be evaluated according to the quality and relevance of the underlying evidence.

VitalPet-RD distinguishes between:

* Canine/feline clinical evidence
* Canine/feline observational evidence
* Canine/feline experimental evidence
* Human clinical evidence
* Laboratory/animal-model evidence
* In-vitro or theoretical evidence

Evidence from humans, rodents, or cell culture should not automatically be presented as equivalent to evidence in dogs or cats.

---

## 2. Dog and Cat Evidence Must Be Distinguished

Dogs and cats differ substantially in:

* Physiology
* Nutrient metabolism
* Dietary requirements
* Drug metabolism
* Ingredient tolerance
* Palatability
* Disease presentation

VitalPet-RD therefore attempts to explicitly identify the target species when evaluating an ingredient, formulation, dose, or scientific claim.

---

## 3. Quantitative Information Requires Evidence

Special attention is given to numerical information such as:

* mg/kg
* mg/day
* mg/animal/day
* % inclusion
* Nutrient targets
* Safety limits
* Clinical doses
* Feeding recommendations

A numerical value should not be presented as an established recommendation simply because it appears scientifically plausible.

When possible, the model should distinguish:

* Published clinical dose
* Published experimental dose
* Manufacturer recommendation
* Internal R&D target
* Safety limit
* Regulatory maximum
* Formulation assumption

---

## 4. No Fabricated Scientific References

VitalPet-RD is explicitly instructed not to invent:

* Scientific papers
* Authors
* Journals
* DOI numbers
* Clinical trials
* Veterinary guidelines
* Regulatory requirements
* Product data

When a source cannot be verified, the model should acknowledge the limitation rather than generate a plausible-looking citation.

---

# Evidence Framework

VitalPet-RD uses the following conceptual evidence hierarchy:

| Level | Evidence                                                                               |
| ----- | -------------------------------------------------------------------------------------- |
| **A** | Canine/feline clinical trial, systematic review, or authoritative veterinary guideline |
| **B** | Canine/feline clinical or observational evidence                                       |
| **C** | Canine/feline experimental or mechanistic evidence                                     |
| **D** | Human clinical evidence                                                                |
| **E** | In-vitro, laboratory animal, theoretical, or other indirect evidence                   |

This classification is intended as a practical R&D framework rather than a formal universal evidence-grading system.

A lower evidence level should not automatically be treated as equivalent to canine/feline clinical evidence.

---

# Formulation Development Framework

For product-development questions, VitalPet-RD follows a structured reasoning process:

```text
Evidence
   ↓
Mechanism
   ↓
Dose rationale
   ↓
Formulation
   ↓
Safety
   ↓
Palatability
   ↓
Stability
   ↓
Manufacturing feasibility
   ↓
Cost
   ↓
Regulatory considerations
   ↓
Claims
```

A formulation should not be evaluated solely on whether the individual ingredients appear scientifically interesting.

Important practical considerations include:

* Target species
* Target function
* Dosage form
* Ingredient compatibility
* Dose feasibility
* Palatability
* Stability
* Manufacturing process
* Cost
* Safety margin
* Regulatory requirements
* Permitted claims

---

# Scientific Evidence vs Product Claims

Scientific evidence and legally permitted marketing claims are different questions.

For example:

```text
Scientific evidence
        ↓
Does the ingredient appear to have an effect?
        ↓
Clinical relevance
        ↓
Safety
        ↓
Product formulation
        ↓
Regulatory classification
        ↓
Permitted claim
```

An ingredient may have scientific evidence for a biological effect without allowing a company to make a disease-treatment claim.

VitalPet-RD therefore treats scientific evidence and regulatory/claim evaluation as separate components.

---

# What VitalPet-RD Is

VitalPet-RD is currently a **domain-specific AI behavior and reasoning layer built on Qwen3-4B**.

The current version does not represent a newly trained foundation model.

Conceptually:

```text
Qwen3-4B
    ↓
VitalPet-RD System Instructions
    ↓
Domain-specific reasoning framework
    ↓
VitalPet-RD
```

The goal of the project is not simply to change the personality of a general-purpose model.

The longer-term objective is to build an R&D system in which the language model works together with structured scientific and proprietary data.

---

# Current Architecture

The current public version is intentionally lightweight:

```text
User
  │
  ▼
VitalPet-RD
  │
  ▼
Qwen3-4B
  │
  ▼
Domain-specific R&D reasoning
```

Future versions are intended to evolve toward:

```text
                         User
                           │
                           ▼
                  VitalPet R&D Platform
                           │
                           ▼
                    R&D Orchestrator
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
   AI Models        Evidence Layer      Private R&D Data
        │                  │                  │
   Qwen3              IRIS / AAHA        Ingredients
   Biomedical AI       FEDIAF            Formulas
   Specialist Models   FDA / AAFCO       Experiments
   Judge/Critic        Scientific Papers  Supplier Data
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
                    R&D Tool Layer
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        Formula Engine  Evidence      Regulatory
        Cost Engine     Engine        Engine
              │            │            │
              └────────────┼────────────┘
                           ▼
                    Verification Layer
                           │
                           ▼
                      R&D Report
```

---

# Roadmap

## Phase 0.1 — Domain Reasoning Layer

Current version.

* Qwen3-4B base model
* VitalPet-RD system instructions
* Pet R&D reasoning framework
* Evidence-awareness rules
* Dog/cat differentiation
* Dose and citation safeguards

---

## Phase 0.2 — Structured Ingredient Database

Planned capabilities:

* Ingredient database
* Species
* Functional category
* Dose range
* Safety information
* Evidence
* Supplier
* Price
* Palatability
* Stability
* Regulatory information

The intended architecture is:

```text
Excel
  ↓
Python importer
  ↓
SQLite / structured database
  ↓
Tool calling
  ↓
VitalPet-RD
```

The structured database is intended to remain separate from the language model's weights.

---

## Phase 0.3 — Formula Engine

Future versions will introduce deterministic formulation calculations.

Potential functions include:

```text
search_ingredients()
get_ingredient()
calculate_formula()
calculate_cost()
compare_formulas()
```

The language model should determine **what needs to be calculated**, while deterministic software performs the actual numerical calculation.

This separation is important because language models should not be relied upon for critical formulation arithmetic.

---

## Phase 0.4 — Scientific Evidence Layer

Future versions may integrate:

* Veterinary guidelines
* Scientific literature
* Clinical studies
* Evidence extraction
* Citation tracking
* Evidence-level classification

The intended principle is:

> **The model reasons over evidence; it does not become the evidence.**

---

## Phase 0.5 — Private R&D Intelligence

A future private deployment may integrate proprietary company information including:

* Ingredient databases
* Historical formulas
* Formula versions
* Internal experiments
* Palatability studies
* Supplier information
* Manufacturing information
* Ingredient costs
* Internal safety data
* Product-development decisions

This information should remain separated from the public repository.

---

# Evaluation

VitalPet-RD is evaluated against the base model using a 20-question R&D benchmark.

The evaluation focuses on:

* Veterinary nutrition
* CKD nutrition
* Nutraceutical formulation
* Ingredient evidence
* Dose reasoning
* Dental products
* Joint products
* Stress-support products
* Palatability
* DMSO/MSM
* Veterinary pharmacology comparisons
* Scientific literature interpretation
* Regulatory claims
* Ingredient database architecture
* Pet R&D AI architecture

The benchmark questions are available in:

```text
evaluation/questions.md
```

The evaluation is intended to measure more than whether an answer "sounds scientific."

Particular attention is paid to:

1. Unsupported numerical claims
2. Fabricated references
3. Species confusion
4. Evidence-level confusion
5. Overconfident conclusions
6. Safety assumptions
7. Regulatory overclaims

---

# Example Research Tasks

VitalPet-RD is intended for questions such as:

```text
Evaluate the evidence for an ingredient in cats with CKD.

Compare the evidence for two functional ingredients.

Design a preliminary canine joint-support formulation.

Evaluate the scientific rationale of an existing pet supplement.

Identify potential formulation conflicts.

Analyze palatability risks.

Compare human evidence with canine/feline evidence.

Evaluate whether a proposed product claim is supported by the available evidence.

Design a structured ingredient database for pet-product R&D.
```

The system should distinguish between:

```text
Established evidence
        ↓
Reasonable interpretation
        ↓
Formulation hypothesis
        ↓
Information requiring verification
```

---

# Limitations

VitalPet-RD should not be treated as a veterinary diagnostic system, medical device, or substitute for professional veterinary judgment.

The current version is particularly limited because it does not yet include:

* A comprehensive veterinary evidence database
* Real-time literature retrieval
* A structured proprietary ingredient database
* Automated regulatory verification
* Deterministic formulation calculations
* Automated citation verification
* Clinical decision support
* Formal validation for veterinary use

The current model may still produce incorrect information.

Therefore, important scientific, safety, veterinary, formulation, and regulatory decisions should be independently verified against authoritative sources and qualified professionals.

---

# Responsible Use

VitalPet-RD is intended to support research and product-development workflows.

It should not be used to:

* Replace veterinary diagnosis
* Replace veterinary treatment
* Establish an unsupported medical dose
* Make unsupported disease-treatment claims
* Treat generated citations as verified references
* Treat human evidence as automatically applicable to dogs or cats
* Treat model-generated calculations as validated formulation calculations

For commercial product development, all critical information should be independently verified before use.

---

# Installation

## Requirements

* Linux, macOS, or Windows with a compatible Ollama installation
* Ollama
* Qwen3-4B

Install Ollama:

```bash
# Install Ollama according to the official Ollama documentation
```

Pull the base model:

```bash
ollama pull qwen3:4b
```

Clone this repository:

```bash
git clone https://github.com/YOUR_USERNAME/vitalpet-rd.git
cd vitalpet-rd

#please note ./data is not uploaded because of company privacy.
#you can refer to info below to buildup this folder manually or contact us for the template
 #ls data
 #cleaned  evidence_vault.db  raw  training  VitalPet_Ingredient_Master_Template.xlsx
```

Create the VitalPet-RD model:

```bash
ollama create vitalpet-rd:0.1 -f Modelfile
```

Run:

```bash
PYTHONPATH=. python3 app/agent.py
```

---

# Repository Structure

```text
vitalpet-rd/
│
├── Modelfile
├── README.md
├── LICENSE
├── .gitignore
│
├── evaluation/
│   ├── questions.md
│   ├── methodology.md
│   ├── qwen3-results.md
│   └── vitalpet-results.md
│
└── examples/
    └── README.md
```

---

# Public vs Private Data

This repository is intended to contain the public components of VitalPet-RD.

Do **not** commit confidential company information.

Examples of information that should normally remain private:

```text
Ingredient purchasing prices
Supplier contracts
Internal formulas
Internal safety data
Internal effective-dose data
Manufacturing specifications
Customer information
Internal experiments
Proprietary product-development data
API keys
Passwords
Credentials
```

A future private deployment may connect these data sources through a structured database and controlled tool-calling interface.

---

# Design Philosophy

VitalPet-RD follows a simple principle:

> **The language model should reason over structured evidence and data rather than pretending to be the source of truth.**

This leads to a separation between:

```text
Model
    ↓
Reasoning

Evidence Database
    ↓
Scientific facts

R&D Database
    ↓
Company knowledge

Formula Engine
    ↓
Deterministic calculations

Regulatory Engine
    ↓
Compliance verification
```

This architecture is intended to make the system more reliable as it grows.

---

# Future Vision

The long-term goal is to develop VitalPet-RD into a specialized AI infrastructure for pet-product research and development.

Potential capabilities include:

```text
Ingredient Intelligence
        +
Scientific Evidence
        +
Formula Design
        +
Cost Optimization
        +
Safety Analysis
        +
Palatability Data
        +
Stability Data
        +
Regulatory Intelligence
        +
Company R&D Knowledge
        ↓
Pet R&D Intelligence Platform
```

The objective is not to build another general-purpose chatbot.

The objective is to build a system that can help R&D teams move from:

```text
Scientific question
        ↓
Evidence
        ↓
Ingredient selection
        ↓
Formula design
        ↓
Cost calculation
        ↓
Safety review
        ↓
Palatability
        ↓
Stability
        ↓
Regulatory review
        ↓
Product development
```

---

# Base Model

VitalPet-RD currently uses:

**Qwen3-4B**

VitalPet-RD does not redistribute the Qwen model weights through this repository.

Users are expected to obtain the base model through the appropriate Qwen/Ollama distribution channel and create the VitalPet-RD model locally using the provided `Modelfile`.

---

# License

The licensing of the VitalPet-RD project should be considered separately from the license of the underlying Qwen model.

See:

```text
LICENSE
```

for the license applicable to the original VitalPet-RD project files.

Users are responsible for complying with the applicable license terms of the underlying base model and any third-party data or software used with VitalPet-RD.

---

# Disclaimer

VitalPet-RD is an experimental research and development project.

It is provided for research, educational, and product-development support purposes.

It does not provide veterinary diagnosis or medical treatment, and generated information should not be considered a substitute for professional veterinary advice or independent scientific and regulatory verification.

---

# Project Status

**Current version:** `0.1`

**Status:** Experimental / Early Development

The project is actively evolving from a domain-specific prompt layer toward a modular pet R&D AI architecture.

---

# Contributing

Contributions related to:

* Companion animal nutrition
* Veterinary evidence evaluation
* Pet nutraceutical research
* Scientific literature analysis
* R&D workflow design
* AI evaluation methodology
* Structured ingredient databases
* Formulation-engine architecture

are welcome.

Please keep proprietary, confidential, or personally identifiable information out of public contributions.

---

# Acknowledgment

VitalPet-RD is built on top of the Qwen3 family of models.

The project aims to explore how a general-purpose language model can be adapted into a specialized research and development assistant through domain-specific instructions, evidence frameworks, structured data, tools, and verification systems.

---

## Vision

**From a pet-product chatbot to a Pet R&D Intelligence Platform.**

````
