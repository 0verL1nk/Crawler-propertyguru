
# BaseUrl
https://api.magiceraser.org
# Create job
## Req
```
POST /api/magiceraser/v3/ai-image-watermark-remove-auto/create-job HTTP/2
Host: api.magiceraser.org
Content-Length: 78180
Sec-Ch-Ua-Platform: "Windows"
Authorization: 
Sec-Ch-Ua: "Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"
Sec-Ch-Ua-Mobile: ?0
Product-Serial: d92a85a2-7f15-40d0-975d-518d1610eb71
Product-Code: 067003
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0
Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryUQ2Ly2R3fBHks7Sj
Accept: */*
Origin: https://magiceraser.org
Sec-Fetch-Site: same-site
Sec-Fetch-Mode: cors
Sec-Fetch-Dest: empty
Referer: https://magiceraser.org/
Accept-Encoding: gzip, deflate
Accept-Language: zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6
Priority: u=1, i

------WebKitFormBoundaryUQ2Ly2R3fBHks7Sj
Content-Disposition: form-data; name="original_image_file"; filename="Horizon-Towers-Orchard-River-Valley-Singapore.jpg"
Content-Type: image/jpeg

ÿØÿà
```
## Resp
```
{
    "code": 100000,
    "result": {
        "job_id": "5725caa4-2be6-4dd1-916f-d62e772624c2"
    },
    "message": {
        "en": "Request Success",
        "zh": "提交任务成功"
    }
}
```
# getJob
## Req
```
GET /api/magiceraser/v2/ai-remove-object/get-job/122a5bcf-3073-4228-9b43-556baee7079b HTTP/2
Host: api.magiceraser.org
Sec-Ch-Ua-Platform: "Windows"
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0
Sec-Ch-Ua: "Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"
Sec-Ch-Ua-Mobile: ?0
Accept: */*
Origin: https://magiceraser.org
Sec-Fetch-Site: same-site
Sec-Fetch-Mode: cors
Sec-Fetch-Dest: empty
Referer: https://magiceraser.org/
Accept-Encoding: gzip, deflate
Accept-Language: zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6
Priority: u=1, i
```
## Resp
```
// doing
{
    "code": 300006,
    "result": {
        "input_url": "https://cdn.magiceraser.org/datarm7/magiceraser/image/remove-watermark/2025-11-03/input/5725caa4-2be6-4dd1-916f-d62e772624c2_original_.jpg?x-oss-process=image/format,jpg/quality,Q_100/resize,m_lfit,w_3000,h_3000"
    },
    "message": {
        "en": "Image generation in progress.",
        "zh": "图片生成中。",
        "id": "Pembuatan gambar sedang berlangsung."
    }
}
// done
{
    "code": 100000,
    "result": {
        "credits_states": 2,
        "need_credits": 0,
        "output_url": [
            "https://cdn.magiceraser.org/datarm7/magiceraser/image/remove-watermark/2025-11-03/output/5725caa4-2be6-4dd1-916f-d62e772624c2.jpg"
        ],
        "input_url": "https://cdn.magiceraser.org/datarm7/magiceraser/image/remove-watermark/2025-11-03/input/5725caa4-2be6-4dd1-916f-d62e772624c2_original_.jpg?x-oss-process=image/format,jpg/quality,Q_100/resize,m_lfit,w_3000,h_3000",
        "job_id": "5725caa4-2be6-4dd1-916f-d62e772624c2",
        "p_credits": 0,
        "s_credits": 0
    },
    "message": {
        "en": "Image generated successfully.",
        "zh": "图片生成成功。"
    }
}
```