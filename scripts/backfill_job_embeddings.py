"""Backfill job embeddings."""

from dotenv import load_dotenv
load_dotenv()

from sqlmodel import Session, select

from app.db import engine
from app.models import Job
from app.services.embedding_service import build_job_text, dumps_embedding, get_embeddings_batched

BATCH_SIZE = 20


def main():
    with Session(engine) as session:
        jobs = session.exec(
            select(Job).where(Job.embedding_json == None)  # noqa
        ).all()

        for i in range(0, len(jobs), BATCH_SIZE):
            batch = jobs[i : i + BATCH_SIZE]

            texts = [build_job_text(job) for job in batch]
            texts = [t for t in texts if t.strip()]

            if not texts:
                continue

            vectors = get_embeddings_batched(texts)

            valid_jobs = [job for job in batch if build_job_text(job).strip()]

            for job, vector in zip(valid_jobs, vectors):
                job.embedding_json = dumps_embedding(vector)
                session.add(job)

            session.commit()
            print(f"Embedded {min(i + BATCH_SIZE, len(jobs))}/{len(jobs)} jobs")


if __name__ == "__main__":
    main()