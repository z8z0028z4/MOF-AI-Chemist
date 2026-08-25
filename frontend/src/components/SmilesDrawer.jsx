import React from 'react';
import { Card, Spin, Alert } from 'antd';

/**
 * SMILES 分子結構圖顯示組件
 *
 * 支援 SVG 和 Base64 PNG 格式的分子結構圖
 * 提供錯誤處理和載入狀態
 */
const SmilesDrawer = ({
  svgStructure,
  pngStructure,
  imageUrl,
  smiles,
  name = "Unknown",
  width = 120,
  height = 120,
  showSmiles = false,
  loading = false,
  error = null
}) => {

  // 如果有錯誤，顯示錯誤信息
  if (error) {
    return (
      <div style={{ width, height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Alert
          message="結構圖載入失敗"
          description={error}
          type="error"
          showIcon
          style={{ fontSize: '12px' }}
        />
      </div>
    );
  }

  // 如果正在載入，顯示載入狀態
  if (loading) {
    return (
      <div style={{
        width,
        height,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        border: '1px dashed #d9d9d9',
        borderRadius: '6px'
      }}>
        <Spin size="small" />
      </div>
    );
  }

  // 優先使用 SVG（向量圖，質量更好）
  if (svgStructure) {
    return (
      <div style={{ textAlign: 'center' }}>
        <div
          style={{
            width,
            height,
            border: '1px solid #f0f0f0',
            borderRadius: '6px',
            overflow: 'hidden',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#fff'
          }}
        >
          <div
            dangerouslySetInnerHTML={{ __html: svgStructure }}
            style={{
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          />
        </div>
        {showSmiles && smiles && (
          <div style={{
            fontSize: '10px',
            color: '#666',
            marginTop: '4px',
            wordBreak: 'break-all',
            maxWidth: width
          }}>
            {smiles}
          </div>
        )}
      </div>
    );
  }

  // 其次使用 PNG（Base64 格式）
  if (pngStructure) {
    return (
      <div style={{ textAlign: 'center' }}>
        <div
          style={{
            width,
            height,
            border: '1px solid #f0f0f0',
            borderRadius: '6px',
            overflow: 'hidden',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#fff'
          }}
        >
          <img
            src={pngStructure}
            alt={`${name} molecular structure`}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'contain'
            }}
          />
        </div>
        {showSmiles && smiles && (
          <div style={{
            fontSize: '10px',
            color: '#666',
            marginTop: '4px',
            wordBreak: 'break-all',
            maxWidth: width
          }}>
            {smiles}
          </div>
        )}
      </div>
    );
  }

  // Finally use an explicitly supplied local/runtime image URL.
  if (imageUrl) {
    return (
      <div style={{ textAlign: 'center' }}>
        <div
          style={{
            width,
            height,
            border: '1px solid #f0f0f0',
            borderRadius: '6px',
            overflow: 'hidden',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#fff'
          }}
        >
          <img
            src={imageUrl}
            alt={`${name} molecular structure`}
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
        </div>
        {showSmiles && smiles && (
          <div style={{ fontSize: '10px', color: '#666', marginTop: '4px', wordBreak: 'break-all', maxWidth: width }}>
            {smiles}
          </div>
        )}
      </div>
    );
  }

  // 如果沒有結構圖，顯示預設狀態
  return (
    <div style={{ textAlign: 'center' }}>
      <div
        style={{
          width,
          height,
          border: '1px dashed #d9d9d9',
          borderRadius: '6px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#fafafa',
          color: '#999',
          fontSize: '12px'
        }}
      >
        無結構圖
      </div>
      {showSmiles && smiles && (
        <div style={{
          fontSize: '10px',
          color: '#666',
          marginTop: '4px',
          wordBreak: 'break-all',
          maxWidth: width
        }}>
          {smiles}
        </div>
      )}
    </div>
  );
};

export default SmilesDrawer;
