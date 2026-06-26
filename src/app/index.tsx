import { useState, useRef } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, Image, ActivityIndicator } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';

export default function App() {
  const [permission, requestPermission] = useCameraPermissions();
  const [photo, setPhoto] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [extractedData, setExtractedData] = useState<{ merchant: string; total: string; date: string } | null>(null);
  const cameraRef = useRef<CameraView>(null);

  if (!permission) {
    return <View />;
  }

  if (!permission.granted) {
    return (
      <View style={styles.container}>
        <Text style={styles.text}>Camera permission is required.</Text>
        <TouchableOpacity style={styles.permissionButton} onPress={requestPermission}>
          <Text style={styles.buttonText}>Grant Permission</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const takePicture = async () => {
    if (cameraRef.current) {
      const photoData = await cameraRef.current.takePictureAsync({ base64: true });
      if (photoData && photoData.uri) {
        setPhoto(photoData.uri);
        analyzePhoto(photoData.base64);
      }
    }
  };

  const analyzePhoto = async (base64Image: string | undefined) => {
    setIsAnalyzing(true);

    setTimeout(() => {
      setExtractedData({
        merchant: "Tech Store Inc.",
        total: "299.99",
        date: "2026-06-23"
      });
      setIsAnalyzing(false);
    }, 2500);
  };

  const reset = () => {
    setPhoto(null);
    setExtractedData(null);
  };

  if (photo) {
    return (
      <View style={styles.container}>
        <Image source={{ uri: photo }} style={styles.camera} />
        <View style={styles.overlay}>
          {isAnalyzing ? (
            <View style={styles.card}>
              <ActivityIndicator size="large" color="#007AFF" />
              <Text style={styles.cardText}>Analyzing receipt...</Text>
            </View>
          ) : extractedData ? (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Success!</Text>
              <Text style={styles.cardText}>Merchant: {extractedData.merchant}</Text>
              <Text style={styles.cardText}>Total: ${extractedData.total}</Text>
              <Text style={styles.cardText}>Date: {extractedData.date}</Text>
              <TouchableOpacity style={styles.actionButton} onPress={reset}>
                <Text style={styles.buttonText}>Scan Another</Text>
              </TouchableOpacity>
            </View>
          ) : null}
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView style={styles.camera} facing="back" ref={cameraRef}>
        <View style={styles.buttonContainer}>
          <TouchableOpacity style={styles.captureButton} onPress={takePicture}>
            <View style={styles.captureInner} />
          </TouchableOpacity>
        </View>
      </CameraView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  camera: { flex: 1 },
  text: { color: '#fff', textAlign: 'center', marginBottom: 20, fontSize: 16 },
  buttonContainer: { position: 'absolute', bottom: 50, width: '100%', alignItems: 'center' },
  permissionButton: { backgroundColor: '#007AFF', padding: 15, borderRadius: 10, alignSelf: 'center' },
  actionButton: { backgroundColor: '#007AFF', padding: 12, borderRadius: 8, marginTop: 15, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
  captureButton: { width: 80, height: 80, borderRadius: 40, backgroundColor: 'rgba(255, 255, 255, 0.3)', justifyContent: 'center', alignItems: 'center' },
  captureInner: { width: 65, height: 65, borderRadius: 32.5, backgroundColor: '#fff' },
  overlay: { ...StyleSheet.absoluteFillObject, justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.6)' },
  card: { backgroundColor: '#fff', padding: 25, borderRadius: 15, width: '80%', alignItems: 'center', shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.25, shadowRadius: 3.84, elevation: 5 },
  cardTitle: { fontSize: 22, fontWeight: 'bold', marginBottom: 15, color: '#333' },
  cardText: { fontSize: 16, marginBottom: 8, color: '#555', marginTop: 10 }
});
