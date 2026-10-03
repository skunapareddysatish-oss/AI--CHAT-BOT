from app.embeddings import embed

vectors = embed([
    "Artificial Intelligence",
    "Machine Learning",
    "Deep Learning"
])

print("Vectors:", len(vectors))
print("Dimensions:", len(vectors[0]))