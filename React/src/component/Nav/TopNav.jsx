import React, { useState, useEffect } from 'react'
import './TopNav.css'
import maleAvatar from '../../assets/images/male.jpg'
import femaleAvatar from '../../assets/images/female.jpg'

const TopNav = ({ currentPage = 'Dashboard', onStepClick, gender = 'male' }) => {
  const [currentStep, setCurrentStep] = useState(1) // 현재 진행상황
  
  const steps = [
    { id: 1, name: 'START', page: 'START' },
    { id: 2, name: 'RPA', page: 'RPA' },
    { id: 3, name: 'Python', page: 'Python' },
    { id: 4, name: 'Dashboard', page: 'Dashboard' }
  ]

  // 현재 페이지에 따라 진행상황 업데이트
  useEffect(() => {
    const stepIndex = steps.findIndex(step => step.page === currentPage)
    if (stepIndex !== -1) {
      setCurrentStep(stepIndex + 1)
    }
  }, [currentPage, steps])

  // 진행상황 클릭 핸들러
  const handleStepClick = (step) => {
    setCurrentStep(step.id)
    if (onStepClick) {
      onStepClick(step.page)
    }
  }

  return (
    <div className='top-nav-container'>
        {/* 진행상황 표시 */}
        <div className='progress-indicator'>
          {steps.map((step, index) => (
            <div key={step.id} className={`progress-step ${currentStep >= step.id ? 'active' : ''}`}>
              <div 
                className={`progress-circle ${currentStep >= step.id ? 'active' : ''}`}
                onClick={() => handleStepClick(step)}
              >
                {step.id}
              </div>
              <span className='progress-label'>{step.name}</span>
              {index < steps.length - 1 && (
                <div className={`progress-line ${currentStep > step.id ? 'active' : ''}`}></div>
              )}
            </div>
          ))}
        </div>

        <button className='top-nav-darkmode'>
            <i className="fa-regular fa-moon fa-flip-horizontal"></i>
        </button>

        <button className='top-nav-bell'>
            <i className="fa-regular fa-bell"></i>
        </button>

        <button className="top-nav-user">
            <img src={gender === 'female' ? femaleAvatar : maleAvatar} alt="avatar" />
            <ul>
                <li>Welcome back,</li>
                <li>JEON</li>
            </ul>
            <i className="fa-solid fa-chevron-down"></i>
        </button>
    </div>
  )
}

export default TopNav
