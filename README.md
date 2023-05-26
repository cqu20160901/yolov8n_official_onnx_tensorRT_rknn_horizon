# yolov8n_official_onnx_tensorRT_rknn_horizon
yolov8n 部署版，基于官方的导出onnx脚本导出onnx模型，在不同平台上进行部署测试，便于移植不同平台（onnx、tensorRT、rknn、Horizon）。

# 文件夹结构说明

yolov8_onnx_offical：使用官方提供的导出onnx方式导出的onnx模型、测试图像、测试结果、测试demo脚本。直接用官方提供的导出onnx方式，转换成板端模型报错，解码部分anchors和strides的操作不支持，因需要将移到后处理中进行。

### 修改部分

以下是修改了导出onnx的方式导出的onnx 进行的转换其他模型测试

导出onxx修改：../ultralytics/nn/modules/head.py 文件修改如下一行

```
# y = torch.cat((dbox, cls.sigmoid()), 1)              # 官方代码
y = torch.cat((self.dfl(box), cls.sigmoid()), 1)       # 导出本示例中的onnx修改行
```

导出onn方式
```
# 导出 onnx
from ultralytics import YOLO

model = YOLO('./weights/yolov8n_relu_20class.pt')
success = model.export(format="onnx")
```


### 文件夹说明
yolov8n_onnx：onnx模型、测试图像、测试结果、测试demo脚本

yolov8n_TensorRT：TensorRT版本模型、测试图像、测试结果、测试demo脚本、onnx模型、onnx2tensorRT脚本(tensorRT-7.2.3.4)

yolov8n_rknn：rknn模型、测试（量化）图像、测试结果、onnx2rknn转换测试脚本

yolov8n_horizon：地平线模型、测试（量化）图像、测试结果、转换测试脚本、测试量化后onnx模型脚本


# 测试效果
![image](https://github.com/cqu20160901/yolov8n_official_onnx_tensorRT_rknn_horizon/blob/main/yolov8_onnx/test_onnx_result.jpg)

（注：图片来源VOC）

# 特别说明
说明：推理测试预处理没有考虑等比率缩放，激活函数 SiLU 用 Relu 进行了替换。由于使用的是 VOC 数据进行训练的（类别是20类），且迭代的次数不多，效果并不是很好，仅供测试流程用。
导出onnx的方式参考[yolov8 官方模型进行瑞芯微RKNN和地平线Horizon芯片仿真测试部署](https://blog.csdn.net/zhangqian_1/article/details/130754564)

本实例仓库是基于官方提供的导出onnx模型进行板端芯片部署测试，官方提供到导出onnx模型对应板端芯片部署效率不高。

若追求更优的板端芯片部署，建议参考转为部署而导出的onnx方式，[yolov8 瑞芯微RKNN和地平线Horizon芯片仿真测试部署](https://blog.csdn.net/zhangqian_1/article/details/128918268) 和 [yolov8板端芯片高效部署方式实例代码](https://github.com/cqu20160901/yolov8n_onnx_tensorRT_rknn_horizon)
