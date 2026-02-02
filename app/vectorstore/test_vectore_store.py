import asyncio
from app.vectorstore.operations import retrieve_similar


async def main():
    while True:
        query = input("Enter your query(or 'exit' to quit): ")
        if query.lower() == "exit":
            print("Exiting...")
            break
        results = await retrieve_similar(query=query, k=3)
        print(f"Top 3 similar documents:{results}")

if __name__ == "__main__":
    asyncio.run(main())





# To run this test file, use the command:
# python -m app.vectorstore.test_vectore_store


# There are some sample documents to add to the vector store for testing.
# document_1 = Document(
#     page_content="I had chocolate chip pancakes and scrambled eggs for breakfast this morning.",
#     metadata={"source": "tweet"},
# )

# document_2 = Document(
#     page_content="The weather forecast for tomorrow is cloudy and overcast, with a high of 62 degrees.",
#     metadata={"source": "news"},
# )

# document_3 = Document(
#     page_content="The story of the defeated king and the climbing spider is a timeless tale that highlights the power of perseverance and inner strength in the face of repeated failure. Long ago, there was a brave king who ruled his kingdom with pride and responsibility, but his reign was threatened when powerful enemies attacked his land. The king led his army into battle with courage, believing strongly in victory, yet despite his efforts, he was defeated. Refusing to surrender easily, he regrouped his forces and fought again, but once more he failed. This cycle of effort and defeat repeated itself several times, and with each loss, the king’s confidence weakened. His soldiers grew weary, resources diminished, and hope slowly faded. After suffering continuous defeats, the king finally lost faith in himself and his destiny. Overcome by despair and shame, he fled from the battlefield and sought refuge in a remote forest, where he hid inside a quiet cave to escape from the world and his own thoughts. Sitting alone in the darkness of the cave, the king reflected on his failures and believed that he was cursed to lose no matter how hard he tried. He felt small, powerless, and defeated, convinced that success was meant for others and not for him. As time passed, his restless mind slowly became aware of his surroundings, and his eyes fell upon a small spider on the cave wall. The spider was attempting to climb up the smooth surface, aiming to reach its web near the top. However, the wall was slippery, and the spider fell down before it could succeed. The king watched absentmindedly as the spider tried again, only to slip and fall once more. Again and again, the spider made the same attempt, and each time it failed, tumbling down to the bottom. At first, the king paid little attention, but as the attempts continued, he became more focused on the tiny creature. The spider showed no sign of giving up. Despite its repeated falls, it continued to climb with determination, using all its strength each time. The king counted the attempts silently, noticing that the spider failed many times, yet it never stopped trying. Finally, after numerous unsuccessful efforts, the spider managed to cling firmly to the wall and slowly made its way upward until it reached its web. The spider had succeeded not because it was strong or lucky, but because it refused to give up. This simple scene had a powerful effect on the king. He realized that the spider’s struggle was a reflection of his own journey. Like the spider, he had fallen repeatedly, but unlike the spider, he had allowed failure to break his spirit. The king understood that success was not achieved by avoiding failure, but by continuing to try despite it. The persistence of such a small creature awakened a sense of courage and determination within him. He began to question his earlier belief that he was destined to fail and recognized that true defeat only comes when one stops trying. With renewed hope, the king decided to return and face his challenges once more. He gathered his remaining loyal soldiers, learned from his past mistakes, planned his strategy more carefully, and prepared himself mentally for the struggle ahead. This time, he fought not with arrogance or desperation, but with patience, resilience, and wisdom gained through failure. Though the battle was difficult, his determination did not waver. Eventually, through consistent effort and perseverance, the king emerged victorious and reclaimed his kingdom. The hardships he endured shaped him into a stronger and wiser ruler, one who understood the value of persistence and humility. The story of the defeated king and the climbing spider teaches that failure is a natural part of any journey toward success and that giving up guarantees defeat, while persistence keeps hope alive. It reminds us that even the smallest example can inspire great change and that determination, when sustained through repeated setbacks, has the power to transform despair into victory.",
#     metadata={"source": "tweet"},
# )

# document_4 = Document(
#     page_content="Robbers broke into the city bank and stole $1 million in cash.",
#     metadata={"source": "news"},
# )

# document_5 = Document(
#     page_content="Wow! That was an amazing movie. I can't wait to see it again.",
#     metadata={"source": "tweet"},
# )

# document_6 = Document(
#     page_content="Is the new iPhone worth the price? Read this review to find out.",
#     metadata={"source": "website"},
# )

# document_7 = Document(
#     page_content="The top 10 soccer players in the world right now.",
#     metadata={"source": "website"},
# )

# document_8 = Document(
#     page_content="LangGraph is the best framework for building stateful, agentic applications!",
#     metadata={"source": "tweet"},
# )

# document_9 = Document(
#     page_content="The stock market is down 500 points today due to fears of a recession.",
#     metadata={"source": "news"},
# )

# document_10 = Document(
#     page_content="I have a bad feeling I am going to get deleted :(",
#     metadata={"source": "tweet"},
# )

# documents = [
#     document_1,
#     document_2,
#     document_3,
#     document_4,
#     document_5,
#     document_6,
#     document_7,
#     document_8,
#     document_9,
#     document_10,
# ]