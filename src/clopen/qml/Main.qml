import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: root
    width: 920
    height: 600
    minimumWidth: 780
    minimumHeight: 520
    visible: false
    color: "transparent"
    title: "Clopen"
    flags: Qt.Window | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint

    readonly property bool darkMode: clopen.darkMode
    readonly property color textPrimary: darkMode ? "#F6F7FA" : "#20242A"
    readonly property color textSecondary: darkMode ? "#B6BDC8" : "#68717C"
    readonly property var selected: clopen.selectedGroup

    onClosing: function(close) {
        close.accepted = false
        clopen.hideMain()
    }

    // IMPORTANT: keep the working transparent/blur foundation from v0.5.2.
    // This layer only adds optical glass sheen; it never paints an opaque base.
    GlassPane {
        anchors.fill: parent
        darkMode: root.darkMode
        cornerRadius: 22
        density: root.darkMode ? 0.012 : 0.028
        highlight: root.darkMode ? 0.16 : 0.22
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // LOCKED brand/title-bar geometry. Do not resize/reflow without explicit request.
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 64

            Row {
                x: 22
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10

                Image {
                    id: brandMark
                    width: 44
                    height: 28
                    anchors.verticalCenter: parent.verticalCenter
                    source: root.darkMode ? "../resources/clopen-logo-white.svg" : "../resources/clopen-logo-black.svg"
                    fillMode: Image.PreserveAspectFit
                    asynchronous: false
                    cache: true
                    smooth: true
                    mipmap: false
                    sourceSize.width: 44
                    sourceSize.height: 28
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: -1
                    Text {
                        text: "Clopen"
                        color: root.textPrimary
                        font.pixelSize: 26
                        font.weight: Font.Medium
                        renderType: Text.NativeRendering
                    }
                    Text {
                        text: "组合启动 · 安全关闭"
                        color: root.textSecondary
                        font.pixelSize: 9
                        renderType: Text.NativeRendering
                    }
                }
            }

            Row {
                id: windowControls
                anchors.right: parent.right
                anchors.rightMargin: 18
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6

                GlassButton {
                    width: 48; height: 34
                    text: "刷新"
                    darkMode: root.darkMode
                    quiet: true
                    onClicked: clopen.refresh()
                }
                GlassButton {
                    width: 36; height: 34
                    text: "—"
                    darkMode: root.darkMode
                    quiet: true
                    onClicked: clopen.minimizeMain()
                }
                GlassButton {
                    width: 36; height: 34
                    text: "×"
                    darkMode: root.darkMode
                    quiet: true
                    onClicked: clopen.hideMain()
                }
            }

            DragHandler {
                target: null
                acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                onActiveChanged: if (active) root.startSystemMove()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 18
            Layout.rightMargin: 18
            Layout.topMargin: 8
            Layout.bottomMargin: 18
            spacing: 18

            // LOCKED sidebar width/layout from the approved formal version.
            GlassPane {
                id: sidebar
                Layout.preferredWidth: 232
                Layout.minimumWidth: 232
                Layout.maximumWidth: 232
                Layout.fillHeight: true
                darkMode: root.darkMode
                cornerRadius: 16
                density: root.darkMode ? 0.024 : 0.050
                highlight: root.darkMode ? 0.14 : 0.20

                ColumnLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    anchors.topMargin: 16
                    anchors.bottomMargin: 14
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        Text {
                            text: "软件组合"
                            color: root.textSecondary
                            font.pixelSize: 11
                            font.weight: Font.DemiBold
                            renderType: Text.NativeRendering
                        }
                        Item { Layout.fillWidth: true }
                        GlassButton {
                            text: "＋ 新建"
                            darkMode: root.darkMode
                            quiet: true
                            implicitHeight: 30
                            fontSize: 12
                            onClicked: clopen.newGroup()
                        }
                    }

                    TextField {
                        id: search
                        Layout.fillWidth: true
                        Layout.preferredHeight: 38
                        placeholderText: "搜索组合或软件…"
                        color: root.textPrimary
                        placeholderTextColor: root.textSecondary
                        leftPadding: 12
                        rightPadding: 12
                        topPadding: 0
                        bottomPadding: 0
                        verticalAlignment: TextInput.AlignVCenter
                        font.pixelSize: 13
                        renderType: Text.NativeRendering
                        selectByMouse: true
                        background: GlassPane {
                            darkMode: root.darkMode
                            cornerRadius: 9
                            density: root.darkMode ? 0.032 : 0.065
                            highlight: search.activeFocus ? 0.34 : 0.16
                        }
                    }

                    ListView {
                        id: groupList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.topMargin: 4
                        Layout.bottomMargin: 4
                        clip: true
                        spacing: 5
                        model: clopen.groupItems
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                        delegate: Item {
                            id: groupDelegate
                            required property var modelData
                            width: groupList.width
                            height: visible ? 58 : 0
                            visible: search.text.length === 0 || modelData.name.toLowerCase().indexOf(search.text.toLowerCase()) >= 0

                            GlassPane {
                                anchors.fill: parent
                                darkMode: root.darkMode
                                cornerRadius: 11
                                density: modelData.selected ? (root.darkMode ? 0.050 : 0.095) : 0.0
                                highlight: modelData.selected ? 0.15 : 0.0
                                visible: modelData.selected || groupMouse.containsMouse
                                opacity: modelData.selected ? 1.0 : 0.58
                            }

                            Rectangle {
                                visible: modelData.selected
                                width: 3
                                height: parent.height - 12
                                radius: 2
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                color: "#718CFF"
                            }

                            Text {
                                anchors.left: parent.left
                                anchors.leftMargin: 12
                                anchors.top: parent.top
                                anchors.topMargin: 10
                                text: (modelData.active ? "●" : "○") + "   " + modelData.name
                                color: modelData.selected ? root.textPrimary : root.textSecondary
                                font.pixelSize: 13
                                font.weight: modelData.selected ? Font.DemiBold : Font.Normal
                                renderType: Text.NativeRendering
                            }
                            Text {
                                anchors.left: parent.left
                                anchors.leftMargin: 30
                                anchors.top: parent.top
                                anchors.topMargin: 31
                                text: modelData.count + " 个启动项"
                                color: modelData.selected ? root.textPrimary : root.textSecondary
                                font.pixelSize: 13
                                font.weight: modelData.selected ? Font.DemiBold : Font.Normal
                                renderType: Text.NativeRendering
                            }

                            MouseArea {
                                id: groupMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: clopen.selectGroup(modelData.name)
                            }
                        }

                        Text {
                            anchors.centerIn: parent
                            visible: clopen.groupItems.length === 0
                            text: search.text.length ? "没有搜索结果\n换个组合名或软件名试试" : "还没有组合\n点击“新建”创建第一个组合"
                            horizontalAlignment: Text.AlignHCenter
                            color: root.textSecondary
                            font.pixelSize: 12
                            lineHeight: 1.4
                            renderType: Text.NativeRendering
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        GlassButton {
                            Layout.fillWidth: true
                            implicitHeight: 34
                            text: "编辑组合"
                            darkMode: root.darkMode
                            enabled: root.selected.exists && !root.selected.active
                            onClicked: clopen.editSelected()
                        }
                        GlassButton {
                            Layout.fillWidth: true
                            implicitHeight: 34
                            text: "删除"
                            darkMode: root.darkMode
                            enabled: root.selected.exists && !root.selected.active
                            onClicked: clopen.deleteSelected()
                        }
                    }

                    GlassButton {
                        Layout.fillWidth: true
                        implicitHeight: 34
                        text: "关闭全部活动会话"
                        darkMode: root.darkMode
                        enabled: clopen.anyActive
                        onClicked: clopen.closeAll()
                    }
                }
            }

            ColumnLayout {
                id: contentColumn
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 14

                // Use anchors inside a fixed header item so the title and primary action
                // are guaranteed to share the same right/left grid as the detail card.
                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 58

                    Column {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 3
                        Text {
                            text: root.selected.name
                            color: root.textPrimary
                            font.pixelSize: 22
                            font.weight: Font.Bold
                            renderType: Text.NativeRendering
                        }
                        Text {
                            text: root.selected.meta
                            color: root.textSecondary
                            font.pixelSize: 12
                            renderType: Text.NativeRendering
                        }
                    }

                    GlassButton {
                        id: primaryButton
                        width: 132
                        height: 44
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: clopen.primaryText
                        darkMode: root.darkMode
                        primary: true
                        danger: root.selected.active
                        fontSize: 15
                        enabled: root.selected.exists
                        onClicked: clopen.primaryAction()
                    }

                    Rectangle {
                        width: 8
                        height: 8
                        radius: 4
                        anchors.right: primaryButton.left
                        anchors.rightMargin: 12
                        anchors.verticalCenter: primaryButton.verticalCenter
                        color: root.selected.active ? "#31D887" : "#7B8493"
                        visible: root.selected.exists
                        ToolTip.visible: statusHover.containsMouse
                        ToolTip.text: root.selected.active ? "当前已启动" : "当前未启动"
                        MouseArea { id: statusHover; anchors.fill: parent; hoverEnabled: true }
                    }
                }

                GlassPane {
                    id: detailCard
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    darkMode: root.darkMode
                    cornerRadius: 16
                    density: root.darkMode ? 0.022 : 0.048
                    highlight: root.darkMode ? 0.13 : 0.20

                    ListView {
                        id: entryList
                        anchors.fill: parent
                        anchors.margins: 14
                        model: root.selected.entries
                        spacing: 7
                        clip: true
                        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                        delegate: GlassPane {
                            required property var modelData
                            width: entryList.width
                            height: 58
                            darkMode: root.darkMode
                            cornerRadius: 13
                            density: root.darkMode ? 0.032 : 0.060
                            highlight: root.darkMode ? 0.13 : 0.19

                            Column {
                                anchors.left: parent.left
                                anchors.leftMargin: 14
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 2
                                Text {
                                    text: modelData.name
                                    color: root.textPrimary
                                    font.pixelSize: 13
                                    font.weight: Font.DemiBold
                                    renderType: Text.NativeRendering
                                }
                                Text {
                                    text: modelData.kind + " · " + modelData.mode
                                    color: root.textSecondary
                                    font.pixelSize: 11
                                    renderType: Text.NativeRendering
                                }
                            }
                        }

                        Text {
                            anchors.centerIn: parent
                            visible: root.selected.exists && root.selected.entries.length === 0
                            text: "这个组合还没有启动项"
                            color: root.textSecondary
                            font.pixelSize: 13
                            renderType: Text.NativeRendering
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 18
                    Text {
                        text: "Clopen 配置 · Ctrl + Shift + E"
                        color: root.textSecondary
                        font.pixelSize: 12
                        renderType: Text.NativeRendering
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: clopen.message.length ? clopen.message : (clopen.groupItems.length + " 个组合 · " + (clopen.anyActive ? "有活动会话" : "0 个活动会话"))
                        color: root.textSecondary
                        font.pixelSize: 12
                        elide: Text.ElideRight
                        renderType: Text.NativeRendering
                    }
                    Text {
                        text: "▥"
                        color: root.textSecondary
                        font.pixelSize: 12
                        renderType: Text.NativeRendering
                    }
                }
            }
        }
    }

    MouseArea {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        width: 18
        height: 18
        cursorShape: Qt.SizeFDiagCursor
        onPressed: root.startSystemResize(Qt.RightEdge | Qt.BottomEdge)
    }
}
