from diffusers import StableDiffusionPipeline
import torch
import os
# 关键：开启国内镜像，解决下载超时
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 1. 加载模型（SD1.5，经典通用）
model_id = "runwayml/stable-diffusion-v1-5"
pipe = StableDiffusionPipeline.from_pretrained(
    model_id,
    torch_dtype=torch.float16,  # 半精度，大幅省显存
    # safety_checker=None  # 可选：关闭安全检查（慎用）
)

# 2. 设备切换：GPU(cuda) / CPU
# pipe = pipe.to("cuda")  # 有NVIDIA显卡用这个
pipe = pipe.to("cpu")  # 无GPU，改用CPU（慢）

# 3. 显存优化（显存<8GB必加）
pipe.enable_attention_slicing()  # 减少峰值显存
# pipe.enable_model_cpu_offload()  # 更省显存，适合小显存

# 4. 提示词（正向+反向，决定画质）
prompt = "a cute corgi dog sitting on a moonlit beach, cinematic lighting, 8k, highly detailed, masterpiece"
negative_prompt = "blurry, low resolution, deformed, ugly, disfigured, bad anatomy"  # 排除坏效果

# 5. 生成图片（核心调用）
image = pipe(
    prompt=prompt,
    negative_prompt=negative_prompt,
    num_inference_steps=30,  # 迭代步数，20-50，越高越清晰、越慢
    guidance_scale=7.5,  # 提示词遵循度，7-10最佳
    width=512,  # 宽，SD1.5最佳512
    height=512, # 高
    generator=torch.Generator("cuda").manual_seed(42)  # 固定种子，复现同一张图
).images[0]  # 取第一张图

# 6. 保存&查看
image.save("corgi_moon.png")
image.show()