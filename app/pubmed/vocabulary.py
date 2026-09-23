# app/pubmed/vocabulary.py

# 核心原料同义词与物种靶向映射
INGREDIENT_VOCABULARY = {
    "glucosamine": {
        "standard_name": "Glucosamine",
        "synonyms": ["氨糖", "葡萄糖胺", "glucosamine sulfate", "glucosamine hydrochloride"],
        "target_systems": ["joint", "mobility"]
    },
    "chondroitin": {
        "standard_name": "Chondroitin Sulfate",
        "synonyms": ["软骨素", "硫酸软骨素"],
        "target_systems": ["joint"]
    },
    "omega3": {
        "standard_name": "Omega-3 Fatty Acids",
        "synonyms": ["鱼油", "EPA", "DHA", "fish oil"],
        "target_systems": ["skin", "coat", "cardiovascular", "kidney"]
    },
    "probiotics": {
        "standard_name": "Probiotics",
        "synonyms": ["益生菌", "enterococcus faecium", "bifidobacterium", "lactobacillus"],
        "target_systems": ["gut", "immunity"]
    }
}

# 每日定时巡检的核心原料列表（用英文标准词检索以保证 PubMed 召回）
DAILY_MONITORED_TERMS = [
    "Glucosamine",
    "Chondroitin Sulfate",
    "Omega-3 Fatty Acids",
    "Enterococcus faecium dog cat",
    "Milk Thistle silymarin dog cat",
    "Psyllium husk feline canine"
]

