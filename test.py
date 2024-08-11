import ollama
import json

student = "thomas jefferson"
answer = "Vitamin K [or phylloquinone before mentioned; or menaquinones]"

prompt = """
"{answer}" is the correct answer to a question I gave one of my students. The student said "{student}". Did he get the question right?
Is the student correct? If the student's response is part of the answer, it's correct. If it's unrelated, it's incorrect. Respond in the following JSON format.\n""".format(student=student, answer=answer) + """\n```json{
    "is_correct": <bool>
}```
"""
response = ollama.chat("tinyllm", [
    {
    "role": "user",
    "content": prompt
        
    }
], options=ollama.Options(temperature=0))
print("PROMPT")
print(prompt)
print("===================")
print(response["message"]['content'])
print(json.loads(response['message']['content']))

# import torch
# from transformers import pipeline

# pipe = pipeline("text-generation", model="TinyLlama/TinyLlama-1.1B-Chat-v1.0", torch_dtype=torch.bfloat16, device_map="auto")

# # We use the tokenizer's chat template to format each message - see https://huggingface.co/docs/transformers/main/en/chat_templating,
# messages = [
#     {
#         "role": "system",
#         "content": "You are a friendly chatbot who always responds in the style of a pirate",
#     },
#     {"role": "user", "content": "How many helicopters can a human eat in one sitting?"},
# ]
# prompt = pipe.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
# outputs = pipe(prompt, max_new_tokens=256, do_sample=True, temperature=0.7, top_k=50, top_p=0.95)
# print(outputs[0]["generated_text"])